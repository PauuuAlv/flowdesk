from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import AuditMixin, Base, BaseModel, TimestampMixin


class PlatformPermission(Base, TimestampMixin, AuditMixin):
    """Catálogo de permisos de la administración de plataforma.
    Se llena desde `app.core.platform_permissions.PLATFORM_PERMISSION_CATALOG`."""

    __tablename__ = "platform_permissions"

    code = Column(String(80), primary_key=True)
    module = Column(String(40), nullable=False, index=True)
    description = Column(String(160), nullable=False)


class PlatformRole(BaseModel):
    """Rol del equipo que administra la plataforma (no pertenece a ningún tenant)."""

    __tablename__ = "platform_roles"

    name = Column(String(50), nullable=False, unique=True)
    description = Column(String(160), nullable=False)
    # 'template' = rol por defecto (superadmin / operator / viewer), 'custom' = creado por el equipo.
    origin = Column(String(20), nullable=False, default="custom")
    template_key = Column(String(50), nullable=True, unique=True)
    is_protected = Column(Boolean, nullable=False, default=False)

    permissions = relationship(
        "PlatformRolePermission", cascade="all, delete-orphan", lazy="selectin"
    )

    @property
    def permission_codes(self) -> list[str]:
        return sorted(item.permission_code for item in self.permissions)


class PlatformRolePermission(Base, TimestampMixin, AuditMixin):
    __tablename__ = "platform_role_permissions"

    role_id = Column(
        UUID(as_uuid=True),
        ForeignKey("platform_roles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    permission_code = Column(
        String(80),
        ForeignKey("platform_permissions.code", ondelete="CASCADE"),
        primary_key=True,
    )
