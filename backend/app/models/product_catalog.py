from sqlalchemy import Boolean, Column, String, UniqueConstraint

from app.models.base import BaseModel, TenantMixin


class MeasurementUnit(BaseModel, TenantMixin):
    __tablename__ = "measurement_units"
    __table_args__ = (
        UniqueConstraint("tenant_id", "key", name="uq_measurement_unit_tenant_key"),
        UniqueConstraint("tenant_id", "name", name="uq_measurement_unit_tenant_name"),
    )

    key = Column(String(50), nullable=False)
    name = Column(String(80), nullable=False)
    abbreviation = Column(String(15), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)

class Brand(BaseModel, TenantMixin):
    __tablename__ = "brands"
    __table_args__ = (UniqueConstraint("tenant_id", "name", name="uq_brand_tenant_name"),)

    name = Column(String(100), nullable=False)
    description = Column(String(300), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
