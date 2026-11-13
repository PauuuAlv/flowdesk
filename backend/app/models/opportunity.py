from sqlalchemy import Column, Date, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import BaseModel, TenantMixin


class Opportunity(BaseModel, TenantMixin):
    __tablename__ = "opportunities"

    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"), nullable=False, index=True)
    owner_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(140), nullable=False, index=True)
    amount = Column(Numeric(14, 2), nullable=False, default=0)
    stage = Column(String(30), nullable=False, default="prospecting", index=True)
    probability = Column(Integer, nullable=False, default=10)
    expected_close_date = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)

    client = relationship("Client", lazy="joined")
    owner = relationship("User", lazy="joined")
