from sqlalchemy import Boolean, Column, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import BaseModel, TenantMixin


class Notification(BaseModel, TenantMixin):
    __tablename__ = "notifications"
    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", "event_key", name="uq_notification_user_event"),
    )

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    event_key = Column(String(180), nullable=False)
    notification_type = Column(String(40), nullable=False, index=True)
    title = Column(String(160), nullable=False)
    message = Column(String(300), nullable=False)
    route = Column(String(300), nullable=False)
    is_read = Column(Boolean, nullable=False, default=False, index=True)
