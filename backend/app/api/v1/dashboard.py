from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.activity import Activity
from app.models.client import Client
from app.models.opportunity import Opportunity
from app.models.quote import Quote
from app.models.user import User
from app.schemas.dashboard import (
    DashboardActivity,
    DashboardMetrics,
    DashboardQuote,
    DashboardResponse,
    PipelineStage,
)
from app.security.permissions import require_permission

router = APIRouter()

PIPELINE_STAGES = ("prospecting", "qualification", "proposal", "negotiation")


def _money(value) -> Decimal:
    return Decimal(value or 0).quantize(Decimal("0.01"))


@router.get("", response_model=DashboardResponse)
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("dashboard.view")),
):
    tenant_id = current_user.tenant_id
    now = datetime.now(timezone.utc)

    active_clients = db.query(func.count(Client.id)).filter(
        Client.tenant_id == tenant_id, Client.status == "active"
    ).scalar() or 0

    open_items = db.query(Opportunity).filter(
        Opportunity.tenant_id == tenant_id,
        Opportunity.archived_at.is_(None),
        Opportunity.stage.in_(PIPELINE_STAGES),
    ).all()
    pipeline_value = sum((_money(item.amount) for item in open_items), Decimal("0.00"))
    weighted_pipeline = sum(
        (_money(item.amount) * Decimal(item.probability) / Decimal(100) for item in open_items),
        Decimal("0.00"),
    )

    pending_query = db.query(Activity).filter(
        Activity.tenant_id == tenant_id, Activity.status == "pending"
    )
    pending_activities = pending_query.count()
    overdue_activities = pending_query.filter(Activity.scheduled_at < now).count()

    pending_quotes = db.query(func.count(Quote.id)).filter(
        Quote.tenant_id == tenant_id, Quote.status.in_(("draft", "sent"))
    ).scalar() or 0
    accepted_quotes_value = db.query(func.coalesce(func.sum(Quote.total), 0)).filter(
        Quote.tenant_id == tenant_id, Quote.status == "accepted"
    ).scalar()

    pipeline = []
    for stage in PIPELINE_STAGES:
        stage_items = [item for item in open_items if item.stage == stage]
        pipeline.append(
            PipelineStage(
                stage=stage,
                count=len(stage_items),
                value=sum((_money(item.amount) for item in stage_items), Decimal("0.00")),
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
            folio=f"COT-{item.issue_date.year}-{item.sequence:04d}",
            client_name=item.client.company_name,
            total=_money(item.total),
            status="expired" if item.status == "sent" and item.valid_until < date.today() else item.status,
        )
        for item in quotes
    ]

    return DashboardResponse(
        metrics=DashboardMetrics(
            active_clients=active_clients,
            open_opportunities=len(open_items),
            pipeline_value=_money(pipeline_value),
            weighted_pipeline_value=_money(weighted_pipeline),
            pending_activities=pending_activities,
            overdue_activities=overdue_activities,
            pending_quotes=pending_quotes,
            accepted_quotes_value=_money(accepted_quotes_value),
        ),
        pipeline=pipeline,
        upcoming_activities=upcoming,
        recent_quotes=recent_quotes,
    )
