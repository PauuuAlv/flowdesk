from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class PlatformAdmin(BaseModel):
    """Integrante del equipo de ArmSystem que administra el SaaS completo.

    A PROPÓSITO no hereda TenantMixin: un PlatformAdmin no pertenece a
    ningún tenant, administra TODOS. Por eso vive en su propia tabla y
    nunca se mezcla con la tabla `users` (que sí exige tenant_id NOT NULL
    en todo momento — ver TenantMixin en base.py).

    Lo que puede hacer lo define su rol de plataforma (platform_roles ->
    platform_role_permissions -> platform_permissions). Puede haber varios
    superadministradores; siempre debe quedar al menos uno activo.

    El primer registro se crea vía seed al desplegar la base de datos
    (ver app/scripts/seed_superadmin.py), nunca por un endpoint público.
    """

    __tablename__ = "platform_admins"

    email = Column(String(255), nullable=False, unique=True, index=True)
    hashed_password = Column(String(255), nullable=True)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    # Cuenta principal: la que se crea con SUPERADMIN_EMAIL del .env. Siempre es
    # Superadministrador activo; nadie puede cambiarle el rol ni desactivarla.
    is_owner = Column(Boolean, nullable=False, default=False)
    role_id =Column(UUID(as_uuid=True), ForeignKey("platform_roles.id"), nullable=False, index=True)
    assigned_role = relationship("PlatformRole", lazy="joined")
    invitation_token_hash = Column(String(64), nullable=True, unique=True)
    invitation_expires_at = Column(DateTime(timezone=True), nullable=True)
    # Recuperación de contraseña ("¿Olvidaste tu contraseña?"): un solo enlace
    # vigente por cuenta; pedir otro reemplaza al anterior.
    password_reset_token_hash = Column(String(64), nullable=True, unique=True)
    password_reset_expires_at = Column(DateTime(timezone=True), nullable=True)

    @property
    def role_key(self) -> str:
        """'superadmin' | 'operator' | 'viewer' para roles por defecto, 'custom' si no."""
        if self.assigned_role and self.assigned_role.template_key:
            return self.assigned_role.template_key
        return "custom"

    @property
    def permission_codes(self) -> list[str]:
        return self.assigned_role.permission_codes if self.assigned_role else []
