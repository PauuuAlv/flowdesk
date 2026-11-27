"""Auditoría automática basada en eventos del ORM de SQLAlchemy.

Qué hace (sin que los endpoints tengan que hacer nada):

1. `before_insert` / `before_update`: llena created_by / updated_by (y sus
   `*_type`) de cualquier modelo que tenga AuditMixin, con el actor del request.
2. `after_insert` / `after_update` / `after_delete`: encola una fila de
   auditoría con el estado anterior y el nuevo del registro.
3. `after_flush` de la sesión: inserta las filas encoladas en la MISMA
   transacción (si el cambio hace rollback, su auditoría también).

A qué tabla va cada fila:
- actor `platform_admin`  -> platform_audit_logs (aunque toque datos de una empresa)
- actor `user`            -> tenant_audit_logs de su empresa
- actor `system`          -> tenant_audit_logs si el registro pertenece a una
                             empresa; si no, platform_audit_logs

Limitación: las operaciones masivas (`db.execute(update(...))`,
`query(...).update()/.delete()`) NO pasan por estos eventos. Para esas se usa
`record_event()` con un resumen (por ejemplo al eliminar una empresa).
"""

from __future__ import annotations

import datetime as _dt
import decimal
import enum
import uuid

from sqlalchemy import event, insert, inspect, text
from sqlalchemy.orm import Mapper, Session

from app.core.audit_context import (
    ACTOR_PLATFORM_ADMIN,
    ACTOR_SYSTEM,
    ACTOR_USER,
    AuditContext,
    get_audit_context,
)
from app.models.platform_audit import PlatformAuditLog, TenantAuditLog

# Tablas que no se auditan: las propias bitácoras y tablas técnicas de mucho
# volumen y poco valor (notificaciones, tokens de un solo uso, suscripciones push).
EXCLUDED_TABLES = frozenset({
    "platform_audit_logs",
    "tenant_audit_logs",
    "notifications",
    "password_reset_tokens",
    "push_subscriptions",
})

# Campos de control: no se muestran como "cambios" del registro.
CONTROL_FIELDS = frozenset({
    "created_at", "updated_at", "created_by", "created_by_type", "updated_by", "updated_by_type",
})

MASK = "***"
_SENSITIVE_PARTS = ("password", "token", "secret")
_SENSITIVE_EXACT = frozenset({"p256dh", "auth"})
_MAX_TEXT = 2000

ENTITY_LABELS = {
    "activities": "Actividad",
    "activity_reminders": "Recordatorio de actividad",
    "brands": "Marca",
    "clients": "Cliente",
    "contacts": "Contacto",
    "measurement_units": "Unidad de medida",
    "opportunities": "Oportunidad",
    "opportunity_stage_history": "Historial de etapa",
    "opportunity_stages": "Etapa de oportunidad",
    "permissions": "Permiso",
    "pipelines": "Pipeline",
    "plan_change_requests": "Solicitud de cambio de plan",
    "platform_admins": "Cuenta de plataforma",
    "platform_permissions": "Permiso de plataforma",
    "platform_role_permissions": "Permiso de rol de plataforma",
    "platform_roles": "Rol de plataforma",
    "product_categories": "Categoría de producto",
    "products": "Producto o servicio",
    "quote_items": "Partida de cotización",
    "quotes": "Cotización",
    "role_permissions": "Permiso de rol",
    "roles": "Rol",
    "tenants": "Empresa",
    "users": "Usuario",
}

_OPERATION_VERBS = {"CREATE": "Creó", "UPDATE": "Modificó", "DELETE": "Eliminó"}
# Campos que se usan para nombrar el registro en la descripción.
_NAME_FIELDS = ("name", "company_name", "title", "full_name", "email", "folio", "code", "sku", "key")

_QUEUE_KEY = "_flowdesk_audit_queue"


# --- Serialización ---------------------------------------------------------

def _is_sensitive(key: str) -> bool:
    lowered = key.lower()
    return lowered in _SENSITIVE_EXACT or any(part in lowered for part in _SENSITIVE_PARTS)


def to_json(value):
    """Convierte cualquier valor de columna a algo que se pueda guardar en JSONB."""
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return value if len(value) <= _MAX_TEXT else value[:_MAX_TEXT] + "…"
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, (_dt.datetime, _dt.date, _dt.time)):
        return value.isoformat()
    if isinstance(value, decimal.Decimal):
        return str(value)
    if isinstance(value, enum.Enum):
        return to_json(value.value)
    if isinstance(value, (bytes, bytearray, memoryview)):
        return f"<{len(value)} bytes>"
    if isinstance(value, dict):
        return {str(k): to_json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [to_json(v) for v in value]
    return str(value)


def _safe(key: str, value):
    if value is not None and _is_sensitive(key):
        return MASK
    return to_json(value)


def _snapshot(mapper, state) -> dict:
    """Valores cargados del registro (nunca dispara consultas a la BD)."""
    data = {}
    for attr in mapper.column_attrs:
        if attr.key in CONTROL_FIELDS or attr.key not in state.dict:
            continue
        data[attr.key] = _safe(attr.key, state.dict[attr.key])
    return data


def _column_changes(mapper, state):
    """[(campo, antes, después)] de las columnas que realmente cambiaron."""
    changes = []
    for attr in mapper.column_attrs:
        if attr.key in CONTROL_FIELDS:
            continue
        history = state.attrs[attr.key].history
        if not history.has_changes():
            continue
        before = history.deleted[0] if history.deleted else None
        after = history.added[0] if history.added else None
        if before == after:
            continue
        changes.append((attr.key, before, after))
    return changes


def _primary_key(mapper, state) -> str | None:
    values = []
    for column in mapper.primary_key:
        prop = mapper.get_property_by_column(column)
        values.append(state.dict.get(prop.key))
    if all(v is None for v in values):
        return None
    return ":".join(str(v) for v in values)[:120]


def _display_name(state) -> str | None:
    for field in _NAME_FIELDS:
        value = state.dict.get(field)
        if isinstance(value, str) and value.strip():
            return value.strip()[:80]
    return None


def _record_tenant_id(mapper, state, table: str):
    if table == "tenants":
        return state.dict.get("id")
    if "tenant_id" in mapper.columns:
        return state.dict.get("tenant_id")
    return None


# --- Actor ----------------------------------------------------------------

def _actor_email(connection, ctx: AuditContext) -> str | None:
    """Correo del actor (se consulta una sola vez por request si hace falta)."""
    if ctx.actor_email or not ctx.actor_id:
        return ctx.actor_email
    table = {ACTOR_USER: "users", ACTOR_PLATFORM_ADMIN: "platform_admins"}.get(ctx.actor_type)
    if not table:
        return None
    email = connection.execute(
        text(f"SELECT email FROM {table} WHERE id = :id"), {"id": ctx.actor_id}
    ).scalar()
    ctx.actor_email = email
    return email


def _resolve_scope(ctx: AuditContext, record_tenant_id):
    """('tenant' | 'platform', tenant_id)."""
    if ctx.actor_type == ACTOR_PLATFORM_ADMIN:
        return "platform", record_tenant_id
    if ctx.actor_type == ACTOR_USER:
        tenant_id = record_tenant_id or ctx.tenant_id
        return ("tenant", tenant_id) if tenant_id else ("platform", None)
    return ("tenant", record_tenant_id) if record_tenant_id else ("platform", None)


def _fill_log_context(connection, target, ctx: AuditContext) -> None:
    """Completa una fila de bitácora creada a mano (record_event o código existente)."""
    if not target.actor_type or target.actor_type == ACTOR_SYSTEM:
        target.actor_type = ctx.actor_type
    if not target.actor_email:
        target.actor_email = _actor_email(connection, ctx)
    if isinstance(target, PlatformAuditLog) and target.platform_admin_id is None and ctx.actor_type == ACTOR_PLATFORM_ADMIN:
        target.platform_admin_id = ctx.actor_id
    if isinstance(target, TenantAuditLog) and target.user_id is None and ctx.actor_type == ACTOR_USER:
        target.user_id = ctx.actor_id
    target.operation = target.operation or "EVENT"
    target.ip_address = target.ip_address or ctx.ip_address
    target.user_agent = target.user_agent or ctx.user_agent
    target.http_method = target.http_method or ctx.http_method
    target.endpoint = target.endpoint or ctx.endpoint
    if target.details is None:
        target.details = {}


# --- Eventos del ORM ------------------------------------------------------

def _has_audit_columns(mapper) -> bool:
    return "created_by" in mapper.columns and "updated_by" in mapper.columns


@event.listens_for(Mapper, "before_insert")
def _before_insert(mapper, connection, target):
    ctx = get_audit_context()
    if _has_audit_columns(mapper):
        target.created_by = ctx.effective_actor_id
        target.created_by_type = ctx.actor_type
        target.updated_by = ctx.effective_actor_id
        target.updated_by_type = ctx.actor_type
    if isinstance(target, (PlatformAuditLog, TenantAuditLog)):
        _fill_log_context(connection, target, ctx)


@event.listens_for(Mapper, "before_update")
def _before_update(mapper, connection, target):
    if not _has_audit_columns(mapper):
        return
    if not _column_changes(mapper, inspect(target)):
        return  # SQLAlchemy llama before_update aunque no haya cambios reales
    ctx = get_audit_context()
    target.updated_by = ctx.effective_actor_id
    target.updated_by_type = ctx.actor_type


def _queue(mapper, target, operation: str) -> None:
    table = mapper.local_table.name
    if table in EXCLUDED_TABLES:
        return
    state = inspect(target)
    session = state.session
    if session is None:
        return

    if operation == "UPDATE":
        changes = _column_changes(mapper, state)
        if not changes:
            return
        before = {key: _safe(key, old) for key, old, _new in changes}
        after = {key: _safe(key, new) for key, _old, new in changes}
    elif operation == "CREATE":
        before, after = None, _snapshot(mapper, state)
    else:
        before, after = _snapshot(mapper, state), None

    label = ENTITY_LABELS.get(table, table)
    name = _display_name(state)
    description = f"{_OPERATION_VERBS[operation]} {label.lower()}" + (f" «{name}»" if name else "")
    if operation == "UPDATE":
        description += ": " + ", ".join(key for key in after)

    session.info.setdefault(_QUEUE_KEY, []).append({
        "operation": operation,
        "entity": table,
        "entity_id": _primary_key(mapper, state),
        "record_tenant_id": _record_tenant_id(mapper, state, table),
        "action": f"{table}.{operation.lower()}",
        "description": description[:500],
        "before_data": before,
        "after_data": after,
    })


@event.listens_for(Mapper, "after_insert")
def _after_insert(mapper, connection, target):
    _queue(mapper, target, "CREATE")


@event.listens_for(Mapper, "after_update")
def _after_update(mapper, connection, target):
    _queue(mapper, target, "UPDATE")


@event.listens_for(Mapper, "after_delete")
def _after_delete(mapper, connection, target):
    _queue(mapper, target, "DELETE")


@event.listens_for(Session, "after_flush")
def _write_queue(session, _flush_context):
    pending = session.info.pop(_QUEUE_KEY, None)
    if not pending:
        return
    ctx = get_audit_context()
    connection = session.connection()
    email = _actor_email(connection, ctx)
    now = _dt.datetime.now(_dt.timezone.utc)

    platform_rows, tenant_rows = [], []
    for item in pending:
        scope, tenant_id = _resolve_scope(ctx, item.pop("record_tenant_id"))
        row = {
            "id": uuid.uuid4(),
            "created_at": now,
            "updated_at": now,
            "created_by": ctx.effective_actor_id,
            "created_by_type": ctx.actor_type,
            "updated_by": ctx.effective_actor_id,
            "updated_by_type": ctx.actor_type,
            "actor_type": ctx.actor_type,
            "actor_email": email,
            "tenant_id": tenant_id,
            "details": {},
            "ip_address": ctx.ip_address,
            "user_agent": ctx.user_agent,
            "http_method": ctx.http_method,
            "endpoint": ctx.endpoint,
            **item,
        }
        if scope == "tenant":
            row["user_id"] = ctx.actor_id if ctx.actor_type == ACTOR_USER else None
            tenant_rows.append(row)
        else:
            row["platform_admin_id"] = ctx.actor_id if ctx.actor_type == ACTOR_PLATFORM_ADMIN else None
            platform_rows.append(row)

    if platform_rows:
        connection.execute(insert(PlatformAuditLog.__table__), platform_rows)
    if tenant_rows:
        connection.execute(insert(TenantAuditLog.__table__), tenant_rows)


# --- API para eventos manuales ---------------------------------------------

def record_event(
    db: Session,
    action: str,
    description: str,
    *,
    tenant_id=None,
    details: dict | None = None,
    scope: str | None = None,
    entity: str | None = None,
    entity_id=None,
):
    """Registra un evento que no es un cambio de fila (login, borrado masivo...).

    `scope` fuerza la bitácora ('tenant' | 'platform'); si no se indica se
    decide con las mismas reglas que los cambios automáticos. No hace commit.
    """
    ctx = get_audit_context()
    if scope is None:
        scope, tenant_id = _resolve_scope(ctx, tenant_id)
    model = TenantAuditLog if scope == "tenant" else PlatformAuditLog
    entry = model(
        tenant_id=tenant_id,
        operation="EVENT",
        action=action,
        description=description[:500],
        entity=entity,
        entity_id=str(entity_id) if entity_id is not None else None,
        details=to_json(details or {}),
    )
    db.add(entry)
    return entry


def entity_label(entity: str | None) -> str | None:
    if not entity:
        return None
    return ENTITY_LABELS.get(entity, entity)
