from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import BaseModel, TenantMixin


class User(BaseModel, TenantMixin):
    """Un usuario SIEMPRE pertenece a un tenant (TenantMixin, tenant_id NOT NULL).

    Ciclo de vida:
      1. Un admin (PlatformAdmin o admin del tenant) lo crea -> status='invited',
         hashed_password=NULL, invitation_token con expiración.
      2. El usuario acepta la invitación (POST /auth/register con el token) ->
         define su contraseña -> status='active', invitation_token se limpia.
      3. Un admin puede desactivarlo -> status='disabled' (no se borra el registro).
    """

    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_user_tenant_email"),
    )

    email = Column(String(255), nullable=False, index=True)
    # Nullable: un usuario recién invitado todavía no tiene password.
    hashed_password = Column(String(255), nullable=True)
    full_name = Column(String(255), nullable=True)

    # 'admin': administra su tenant, puede invitar/desactivar usuarios.
    # 'member': usuario normal, sin permisos de administración.
    role = Column(String(50), nullable=False, default="member")

    # 'invited' | 'active' | 'disabled'
    status = Column(String(50), nullable=False, default="invited")

    # Quién lo invitó (otro User del mismo tenant). Nullable porque el primer
    # admin de un tenant lo crea un PlatformAdmin, no otro User.
    invited_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    # Token de invitación: se guarda HASHEADO (igual que un password), el
    # token real en texto plano solo se manda por correo, nunca se persiste.
    invitation_token_hash = Column(String(255), nullable=True, unique=True, index=True)
    invitation_expires_at = Column(DateTime(timezone=True), nullable=True)
    activated_at = Column(DateTime(timezone=True), nullable=True)

    @property
    def is_active(self) -> bool:
        return self.status == "active"
