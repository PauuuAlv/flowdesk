import uuid
from sqlalchemy import Column, DateTime, String, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base

Base = declarative_base()

# Ver app.core.audit_context.SYSTEM_ACTOR_ID (se repite aquí como literal SQL
# para el server_default, que se usa en inserts que no pasan por el ORM).
_SYSTEM_ACTOR_SQL = text("'00000000-0000-0000-0000-000000000000'::uuid")
_SYSTEM_TYPE_SQL = text("'system'")


class TimestampMixin:
    """Agrega created_at / updated_at automáticos a cualquier modelo."""
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())


class AuditMixin:
    """Usuario creador y usuario de la última modificación.

    Los llena automáticamente app.core.audit (eventos del ORM) a partir del
    contexto del request. Como pueden ser usuarios de empresa (`users`) o
    cuentas de plataforma (`platform_admins`), se guarda el id SIN llave
    foránea y un `*_type` que indica de qué tabla es: user | platform_admin |
    system. El actor `system` usa el UUID 00000000-0000-0000-0000-000000000000.
    """
    created_by = Column(UUID(as_uuid=True), nullable=False, server_default=_SYSTEM_ACTOR_SQL)
    created_by_type = Column(String(20), nullable=False, server_default=_SYSTEM_TYPE_SQL)
    updated_by = Column(UUID(as_uuid=True), nullable=False, server_default=_SYSTEM_ACTOR_SQL)
    updated_by_type = Column(String(20), nullable=False, server_default=_SYSTEM_TYPE_SQL)


class TenantMixin:
    """CRÍTICO: toda tabla que pertenezca a un tenant debe heredar esto.
    tenant_id SIEMPRE se resuelve desde el JWT en el middleware,
    nunca se debe aceptar como parámetro directo del cliente (ver Threat Model, sección 19)."""
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)


class BaseModel(Base, TimestampMixin, AuditMixin):
    __abstract__ = True
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
