from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import BaseModel, TenantMixin


class PushSubscription(BaseModel, TenantMixin):
    """Suscripción Web Push (estándar W3C Push API) de un navegador.

    Cada navegador/dispositivo en el que el usuario acepta recibir
    notificaciones genera un `endpoint` único del servicio push del navegador
    (FCM, Mozilla autopush, Apple, WNS...) y un par de claves para cifrar el
    contenido (RFC 8291). El endpoint es globalmente único: si otro usuario
    inicia sesión en el mismo navegador, la suscripción se reasigna.
    """

    __tablename__ = "push_subscriptions"
    __table_args__ = (UniqueConstraint("endpoint", name="uq_push_subscriptions_endpoint"),)

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    endpoint = Column(Text, nullable=False)
    p256dh = Column(String(255), nullable=False)
    auth = Column(String(255), nullable=False)
    user_agent = Column(String(300), nullable=True)
    last_success_at = Column(DateTime(timezone=True), nullable=True)
    failure_count = Column(Integer, nullable=False, default=0)
