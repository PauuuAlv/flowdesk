"""Auditoría de la empresa: solo lectura y solo de la empresa del token."""

import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.audit import record_event
from app.core.config import settings
from app.core.database import get_db
from app.models.platform_audit import TenantAuditLog
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.audit import AuditFiltersResponse, AuditPageResponse
from app.security.permissions import require_permission
from app.services import audit_queries
from app.services.audit_report import MAX_REPORT_ROWS, build_audit_pdf, resolve_timezone

router = APIRouter()


def _filtered_query(db: Session, tenant_id, operation, entity, user_id, search, date_from, date_to):
    query = db.query(TenantAuditLog).filter(TenantAuditLog.tenant_id == tenant_id)
    return audit_queries.apply_filters(
        query, TenantAuditLog, operations=operation, entities=entity, actor_ids=user_id,
        search=search, date_from=date_from, date_to=date_to,
    )


@router.get("", response_model=AuditPageResponse)
def list_tenant_audit(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    operation: list[str] | None = Query(None, description="Repetible: CREATE | UPDATE | DELETE | EVENT"),
    entity: list[str] | None = Query(None, description="Repetible: tabla auditada"),
    user_id: list[uuid.UUID] | None = Query(None, description="Repetible"),
    search: str | None = Query(None, max_length=120),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("audit.view")),
):
    query = _filtered_query(db, current_user.tenant_id, operation, entity, user_id, search, date_from, date_to)
    items, total = audit_queries.paginate(query, TenantAuditLog, page, page_size)
    return AuditPageResponse(
        items=[audit_queries.serialize(item) for item in items],
        total=total, page=page, page_size=page_size,
    )


@router.get("/report.pdf")
def tenant_audit_report(
    operation: list[str] | None = Query(None, description="Repetible: CREATE | UPDATE | DELETE | EVENT"),
    entity: list[str] | None = Query(None, description="Repetible: tabla auditada"),
    user_id: list[uuid.UUID] | None = Query(None, description="Repetible"),
    search: str | None = Query(None, max_length=120),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    tz: str | None = Query(None, max_length=64, description="Zona horaria IANA del usuario"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("audit.view")),
    _can_export: User = Depends(require_permission("audit.export")),
):
    """Reporte PDF con los mismos filtros que la pantalla (máximo MAX_REPORT_ROWS registros).
    Requiere `audit.view` y `audit.export`."""
    zone = resolve_timezone(tz)
    query = _filtered_query(db, current_user.tenant_id, operation, entity, user_id, search, date_from, date_to)
    items, total = audit_queries.paginate(query, TenantAuditLog, 1, MAX_REPORT_ROWS)
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    filters = audit_queries.describe_filters(
        db, TenantAuditLog, zone, operations=operation, entities=entity, actor_ids=user_id,
        search=search, date_from=date_from, date_to=date_to,
    )
    pdf = build_audit_pdf(
        title="Reporte de auditoría",
        subtitle=tenant.name if tenant else "Empresa",
        items=items, total=total, filters=filters,
        generated_by=current_user.email, tz=zone,
        logo_path=Path(settings.MEDIA_ROOT) / "logos" / f"{current_user.tenant_id}.webp",
    )

    # Generar el reporte también queda en la auditoría (después de consultarla).
    record_event(
        db, "audit.report_exported", f"Generó un reporte de auditoría en PDF ({min(total, MAX_REPORT_ROWS)} registros)",
        tenant_id=current_user.tenant_id, details={"filters": dict(filters), "total": total},
    )
    db.commit()

    filename = f"auditoria-{datetime.now(zone).strftime('%Y%m%d-%H%M')}.pdf"
    return StreamingResponse(
        pdf, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/filters", response_model=AuditFiltersResponse)
def tenant_audit_filters(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("audit.view")),
):
    same_tenant = TenantAuditLog.tenant_id == current_user.tenant_id
    return AuditFiltersResponse(
        entities=audit_queries.entity_options(db, TenantAuditLog, same_tenant),
        actors=audit_queries.actor_options(db, TenantAuditLog, same_tenant),
    )
