from sqlalchemy import Column, Date, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import BaseModel, TenantMixin


class OpportunityStageHistory(BaseModel, TenantMixin):
    __tablename__ = "opportunity_stage_history"

    opportunity_id = Column(UUID(as_uuid=True), ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=False, index=True)
    from_stage_key = Column(String(50), nullable=True)
    to_stage_key = Column(String(50), nullable=False)
    probability = Column(Integer, nullable=False)
    expected_close_date = Column(Date, nullable=True)
    note = Column(Text, nullable=True)
    changed_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    changed_by = relationship("User", lazy="joined")
