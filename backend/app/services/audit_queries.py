"""Consultas de las bitácoras de auditoría (empresa y plataforma)."""

from datetime import datetime

from sqlalchemy import func, or_
from sqlalchemy.orm import Query, Session

from app.core.audit import entity_label
from app.models.platform_audit import TenantAuditLog
from app.schemas.audit import AuditEntryResponse, AuditFilterOption

OPERATIONS = ("CREATE", "UPDATE", "DELETE", "EVENT")


def _clean_operations(operations) -> list[str]:
    return [op.upper() for op in (operations or []) if op and op.upper() in OPERATIONS]


def _clean(values) -> list:
    return [value for value in (values or []) if value]


def _actor_column(model):
    return model.user_id if model is TenantAuditLog else model.platform_admin_id


def apply_filters(
    query: Query,
    model,
    *,
    operations: list[str] | None = None,
    entities: list[str] | None = None,
    actor_ids: list | None = None,
    search: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> Query:
    """Cada filtro acepta varios valores (se combinan con OR dentro del filtro
    y con AND entre filtros distintos)."""
    if ops := _clean_operations(operations):
        query = query.filter(model.operation.in_(ops))
    if entity_values := _clean(entities):
        query = query.filter(model.entity.in_(entity_values))
    if actors := _clean(actor_ids):
        query = query.filter(_actor_column(model).in_(actors))
    if date_from:
        query = query.filter(model.created_at >= date_from)
    if date_to:
        query = query.filter(model.created_at <= date_to)
    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.filter(or_(
            model.description.ilike(term),
            model.actor_email.ilike(term),
            model.endpoint.ilike(term),
            model.entity_id.ilike(term),
            model.ip_address.ilike(term),
        ))
    return query


_OPERATION_FILTER_LABELS = {"CREATE": "Creación", "UPDATE": "Modificación", "DELETE": "Eliminación", "EVENT": "Evento"}


def describe_filters(
    db: Session,
    model,
    tz,
    *,
    operations: list[str] | None = None,
    entities: list[str] | None = None,
    actor_ids: list | None = None,
    search: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    tenant_name: str | None = None,
) -> list[tuple[str, str]]:
    """Filtros aplicados en texto legible, para el encabezado del reporte."""
    result: list[tuple[str, str]] = []
    if tenant_name:
        result.append(("Empresa", tenant_name))
    if ops := _clean_operations(operations):
        result.append(("Acción", ", ".join(_OPERATION_FILTER_LABELS[op] for op in ops)))
    if entity_values := _clean(entities):
        result.append(("Módulo", ", ".join(entity_label(entity) or entity for entity in entity_values)))
    if actors := _clean(actor_ids):
        column = _actor_column(model)
        emails = dict(
            db.query(column, func.max(model.actor_email)).filter(column.in_(actors)).group_by(column).all()
        )
        result.append(("Usuario", ", ".join(emails.get(actor) or str(actor) for actor in actors)))
    if date_from:
        result.append(("Desde", date_from.astimezone(tz).strftime("%d/%m/%Y")))
    if date_to:
        result.append(("Hasta", date_to.astimezone(tz).strftime("%d/%m/%Y")))
    if search and search.strip():
        result.append(("Búsqueda", search.strip()))
    return result


def paginate(query: Query, model, page: int, page_size: int):
    total = query.order_by(None).count()
    items = (
        query.order_by(model.created_at.desc(), model.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total


def serialize(item, tenant_name: str | None = None) -> AuditEntryResponse:
    if isinstance(item, TenantAuditLog):
        actor_id = item.user_id
    else:
        actor_id = item.platform_admin_id
    return AuditEntryResponse(
        id=str(item.id),
        created_at=item.created_at,
        operation=item.operation,
        action=item.action,
        description=item.description,
        entity=item.entity,
        entity_label=entity_label(item.entity),
        entity_id=item.entity_id,
        actor_type=item.actor_type or "system",
        actor_id=str(actor_id) if actor_id else None,
        actor_email=item.actor_email,
        ip_address=item.ip_address,
        user_agent=item.user_agent,
        http_method=item.http_method,
        endpoint=item.endpoint,
        before_data=item.before_data,
        after_data=item.after_data,
        details=item.details or {},
        tenant_id=str(item.tenant_id) if item.tenant_id else None,
        tenant_name=tenant_name,
    )


def entity_options(db: Session, model, *filters) -> list[AuditFilterOption]:
    rows = db.query(model.entity).filter(model.entity.isnot(None), *filters).distinct().all()
    options = [AuditFilterOption(value=entity, label=entity_label(entity) or entity) for (entity,) in rows]
    return sorted(options, key=lambda option: option.label)


def actor_options(db: Session, model, *filters) -> list[AuditFilterOption]:
    column = _actor_column(model)
    rows = (
        db.query(column, func.max(model.actor_email))
        .filter(column.isnot(None), *filters)
        .group_by(column)
        .all()
    )
    options = [AuditFilterOption(value=str(actor_id), label=email or str(actor_id)) for actor_id, email in rows]
    return sorted(options, key=lambda option: option.label.lower())

