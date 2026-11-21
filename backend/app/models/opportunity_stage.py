from sqlalchemy import Boolean, Column, Integer, String, UniqueConstraint

from app.models.base import BaseModel, TenantMixin


class OpportunityStage(BaseModel, TenantMixin):
    __tablename__ = "opportunity_stages"
    __table_args__ = (
        UniqueConstraint("tenant_id", "key", name="uq_opportunity_stage_tenant_key"),
        UniqueConstraint("tenant_id", "name", name="uq_opportunity_stage_tenant_name"),
    )

    key = Column(String(50), nullable=False)
    name = Column(String(80), nullable=False)
    position = Column(Integer, nullable=False, default=1)
    stage_type = Column(String(20), nullable=False, default="normal")
    default_probability = Column(Integer, nullable=False, default=10)
    is_active = Column(Boolean, nullable=False, default=True)
