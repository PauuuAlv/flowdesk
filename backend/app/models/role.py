from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base, BaseModel, TenantMixin


class Permission(Base):
    """Catálogo GLOBAL de permisos del sistema (no pertenece a ningún tenant).
    Se llena desde `app.core.permissions.PERMISSION_CATALOG`."""

    __tablename__ = "permissions"

    code = Column(String(80), primary_key=True)
    module = Column(String(40), nullable=False, index=True)
    description = Column(String(160), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Role(BaseModel, TenantMixin):
    """Rol de UN tenant. Cada tenant tiene sus propios roles (los 3 por defecto
    se crean al dar de alta la empresa) y solo él puede verlos y usarlos."""

    __tablename__ = "roles"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_role_tenant_name"),
        UniqueConstraint("tenant_id", "template_key", name="uq_role_tenant_template"),
        # Permite que role_permissions/users referencien (id, tenant_id) y así la
        # base de datos garantiza que nunca se mezclen roles de otro tenant.
        UniqueConstraint("id", "tenant_id", name="uq_role_id_tenant"),
    )

    name = Column(String(50), nullable=False)
    description = Column(String(160), nullable=False)
    # 'template' = rol por defecto (admin / member / viewer), 'custom' = creado por el tenant.
    origin = Column(String(20), nullable=False, default="custom")
    template_key = Column(String(50), nullable=True)
    is_protected = Column(Boolean, nullable=False, default=False)

    permissions = relationship(
        "RolePermission", cascade="all, delete-orphan", lazy="selectin"
    )

    @property
    def permission_codes(self) -> list[str]:
        return sorted(item.permission_code for item in self.permissions)


class RolePermission(Base):
    """Relación rol ↔ permiso dentro de un tenant."""

    __tablename__ = "role_permissions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["role_id", "tenant_id"],
            ["roles.id", "roles.tenant_id"],
            ondelete="CASCADE",
            name="fk_role_permissions_role_tenant",
        ),
    )

    role_id = Column(UUID(as_uuid=True), primary_key=True)
    permission_code = Column(
        String(80),
        ForeignKey("permissions.code", ondelete="CASCADE", name="fk_role_permissions_permission"),
        primary_key=True,
    )
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
