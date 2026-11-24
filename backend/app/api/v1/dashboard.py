from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.currencies import tenant_currency
from app.core.database import get_db
from app.models.activity import Activity
from app.models.client import Client
from app.models.opportunity import Opportunity
from app.models.opportunity_stage import OpportunityStage
from app.models.pipeline import Pipeline
from app.models.quote import Quote
from app.models.user import User
from app.schemas.dashboard import (
    DashboardActivity,
    DashboardMetrics,
    DashboardQuote,
    DashboardResponse,
    MoneyTotal,
    PipelineStage,
)
from app.security.permissions import require_permission

router = APIRouter()

def _money(value) -> Decimal:
    return Decimal(value or 0).quantize(Decimal("0.01"))


def _totals(pairs, default_currency: str) -> list[MoneyTotal]:
    """Suma (moneda, importe) por moneda. La moneda de la empresa va primero y
    siempre aparece (aunque sea en cero); las demás, solo si tienen importes."""
    sums: dict[str, Decimal] = {default_currency: Decimal("0.00")}
    for currency, amount in pairs:
        sums[currency] = sums.get(currency, Decimal("0.00")) + _money(amount)
    ordered = [default_currency] + sorted(c for c in sums if c != default_currency)
    return [MoneyTotal(currency=c, amount=_money(sums[c])) for c in ordered]


@router.get("", response_model=DashboardResponse)
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("dashboard.view")),
):
    tenant_id = current_user.tenant_id
    now = datetime.now(timezone.utc)
    currency = tenant_currency(db, tenant_id)

    active_clients = db.query(func.count(Client.id)).filter(
        Client.tenant_id == tenant_id, Client.status == "active"
    ).scalar() or 0

    # Etapas abiertas agrupadas por pipeline: el predeterminado primero.
    pipeline_stages = db.query(OpportunityStage).join(Pipeline, Pipeline.id == OpportunityStage.pipeline_id).filter(
        OpportunityStage.tenant_id == tenant_id,
        OpportunityStage.stage_type == "normal",
        Pipeline.is_active.is_(True),
    ).order_by(Pipeline.is_default.desc(), Pipeline.position, Pipeline.name, OpportunityStage.position).all()
    pipeline_names = {p.id: p.name for p in db.query(Pipeline).filter(Pipeline.tenant_id == tenant_id)}
    pipeline_stage_keys = tuple(stage.key for stage in pipeline_stages)
    open_items = db.query(Opportunity).filter(
        Opportunity.tenant_id == tenant_id,
        Opportunity.archived_at.is_(None),
        Opportunity.stage.in_(pipeline_stage_keys),
    ).all()
    pipeline_value = _totals(((item.currency, item.amount) for item in open_items), currency)
    weighted_pipeline = _totals(
        ((item.currency, _money(item.amount) * Decimal(item.probability) / Decimal(100)) for item in open_items),
        currency,
    )

    pending_query = db.query(Activity).filter(
        Activity.tenant_id == tenant_id, Activity.status == "pending"
    )
    pending_activities = pending_query.count()
    overdue_activities = pending_query.filter(Activity.scheduled_at < now).count()

    pending_quotes = db.query(func.count(Quote.id)).filter(
        Quote.tenant_id == tenant_id, Quote.status.in_(("draft", "sent"))
    ).scalar() or 0
    accepted_quotes_value = _totals(
        db.query(Quote.currency, func.sum(Quote.total)).filter(
            Quote.tenant_id == tenant_id, Quote.status == "accepted"
        ).group_by(Quote.currency).all(),
        currency,
    )

    pipeline = []
    for stage in pipeline_stages:
        stage_items = [item for item in open_items if item.stage == stage.key]
        pipeline.append(
            PipelineStage(
                pipeline_id=str(stage.pipeline_id),
                pipeline_name=pipeline_names.get(stage.pipeline_id, ""),
                stage=stage.key,
                stage_name=stage.name,
                color=stage.color,
                count=len(stage_items),
                value=_totals(((item.currency, item.amount) for item in stage_items), currency),
            )
        )

    activities = pending_query.order_by(Activity.scheduled_at.asc()).limit(6).all()
    upcoming = [
        DashboardActivity(
            id=str(item.id),
            title=item.title,
            activity_type=item.activity_type,
            client_name=item.client.company_name,
            scheduled_at=item.scheduled_at,
            is_overdue=item.scheduled_at < now,
        )
        for item in activities
    ]

    quotes = db.query(Quote).filter(Quote.tenant_id == tenant_id).order_by(
        Quote.created_at.desc()
    ).limit(5).all()
    recent_quotes = [
        DashboardQuote(
            id=str(item.id),
            folio=f"{item.prefix or 'COT'}-{item.issue_date.year}-{item.sequence:04d}",
            client_name=item.client.company_name,
            total=_money(item.total),
            currency=item.currency,
            status="expired" if item.status == "sent" and item.valid_until < date.today() else item.status,
        )
        for item in quotes
    ]

    return DashboardResponse(
        metrics=DashboardMetrics(
            active_clients=active_clients,
            open_opportunities=len(open_items),
            currency=currency,
            pipeline_value=pipeline_value,
            weighted_pipeline_value=weighted_pipeline,
            pending_activities=pending_activities,
            overdue_activities=overdue_activities,
            pending_quotes=pending_quotes,
            accepted_quotes_value=accepted_quotes_value,
        ),
        pipeline=pipeline,
        upcoming_activities=upcoming,
        recent_quotes=recent_quotes,
    )
