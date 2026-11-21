from sqlalchemy import Column, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.models.base import BaseModel


class PlatformAuditLog(BaseModel):
    __tablename__ = "platform_audit_logs"

    platform_admin_id = Column(
        UUID(as_uuid=True), ForeignKey("platform_admins.id", ondelete="SET NULL"), nullable=True
    )
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(80), nullable=False, index=True)
    description = Column(String(500), nullable=False)
    details = Column(JSONB, nullable=False, default=dict)
