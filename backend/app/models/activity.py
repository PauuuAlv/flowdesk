from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import BaseModel, TenantMixin


class Activity(BaseModel, TenantMixin):
    __tablename__ = "activities"

    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False, index=True)
    opportunity_id = Column(UUID(as_uuid=True), ForeignKey("opportunities.id"), nullable=True, index=True)
    owner_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    activity_type = Column(String(20), nullable=False, index=True)
    title = Column(String(140), nullable=False)
    description = Column(Text, nullable=True)
    scheduled_at = Column(DateTime(timezone=True), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="pending", index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    client = relationship("Client", lazy="joined")
    opportunity = relationship("Opportunity", lazy="joined")
    owner = relationship("User", lazy="joined")
