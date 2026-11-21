from sqlalchemy import Column, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import BaseModel, TenantMixin


class PlanChangeRequest(BaseModel, TenantMixin):
    __tablename__ = "plan_change_requests"

    requested_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    current_plan_key = Column(String(30), nullable=False)
    requested_plan_key = Column(String(30), nullable=False)
    status = Column(String(30), nullable=False, default="pending", index=True)
    note = Column(Text, nullable=True)
    resolved_by_admin_id = Column(UUID(as_uuid=True), ForeignKey("platform_admins.id"), nullable=True)
