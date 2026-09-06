from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import BaseModel, TenantMixin


class PasswordResetToken(BaseModel, TenantMixin):
    """Un registro por cada solicitud de forgot-password.

    Igual que la invitación: el token se guarda hasheado (token_hash),
    el valor real en texto plano solo se manda por correo y nunca se persiste.
    Hereda TenantMixin porque siempre está atado a un User de un tenant
    específico (no a un PlatformAdmin).
    """

    __tablename__ = "password_reset_tokens"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    token_hash = Column(String(255), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used_at = Column(DateTime(timezone=True), nullable=True)
