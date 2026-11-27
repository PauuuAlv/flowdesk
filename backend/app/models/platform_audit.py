"""Bitácoras de auditoría.

- `platform_audit_logs`: acciones de las cuentas de la administración de
  Flowdesk (y procesos del sistema que no pertenecen a una empresa).
- `tenant_audit_logs`: acciones de los usuarios de cada empresa.

Ambas tablas son de solo inserción (no hay endpoints para editar ni borrar) y
NO tienen llaves foráneas hacia usuarios ni empresas: el historial debe
sobrevivir aunque se elimine el usuario o la empresa.

Cada fila es un CREATE / UPDATE / DELETE de un registro (lo genera
automáticamente app.core.audit) o un EVENT (login, eliminación de empresa,
etc.). `before_data` / `after_data` guardan cómo estaba y cómo quedó el
registro; en UPDATE solo se guardan los campos que cambiaron.
"""

from sqlalchemy import Column, Index, String
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.models.base import BaseModel


class _AuditLogColumns:
    actor_type = Column(String(20), nullable=False, default="system")
    actor_email = Column(String(255), nullable=True)
    tenant_id = Column(UUID(as_uuid=True), nullable=True)
    operation = Column(String(10), nullable=False, default="EVENT")
    action = Column(String(80), nullable=False, index=True)
    description = Column(String(500), nullable=False)
    entity = Column(String(80), nullable=True)
    entity_id = Column(String(120), nullable=True)
    before_data = Column(JSONB, nullable=True)
    after_data = Column(JSONB, nullable=True)
    details = Column(JSONB, nullable=False, default=dict)
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(String(500), nullable=True)
    http_method = Column(String(10), nullable=True)
    endpoint = Column(String(255), nullable=True)


class PlatformAuditLog(BaseModel, _AuditLogColumns):
    __tablename__ = "platform_audit_logs"
    __table_args__ = (
        Index("ix_platform_audit_logs_created_at", "created_at"),
        Index("ix_platform_audit_logs_tenant_id", "tenant_id"),
    )

    # Cuenta de plataforma que hizo la acción (sin FK, ver docstring del módulo).
    platform_admin_id = Column(UUID(as_uuid=True), nullable=True, index=True)


class TenantAuditLog(BaseModel, _AuditLogColumns):
    __tablename__ = "tenant_audit_logs"
    __table_args__ = (
        Index("ix_tenant_audit_logs_tenant_created", "tenant_id", "created_at"),
        Index("ix_tenant_audit_logs_tenant_entity", "tenant_id", "entity"),
    )

    tenant_id = Column(UUID(as_uuid=True), nullable=False)
    # Usuario de la empresa que hizo la acción (sin FK, ver docstring del módulo).
    user_id = Column(UUID(as_uuid=True), nullable=True, index=True)
