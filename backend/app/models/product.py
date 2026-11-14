from sqlalchemy import Column, Numeric, String, Text, UniqueConstraint

from app.models.base import BaseModel, TenantMixin


class Product(BaseModel, TenantMixin):
    __tablename__ = "products"
    __table_args__ = (UniqueConstraint("tenant_id", "sku", name="uq_product_tenant_sku"),)

    name = Column(String(140), nullable=False, index=True)
    sku = Column(String(50), nullable=False, index=True)
    description = Column(Text, nullable=True)
    category = Column(String(80), nullable=True, index=True)
    item_type = Column(String(20), nullable=False, default="service", index=True)
    unit = Column(String(30), nullable=False, default="service")
    base_price = Column(Numeric(14, 2), nullable=False, default=0)
    tax_rate = Column(Numeric(5, 2), nullable=False, default=16)
    status = Column(String(20), nullable=False, default="active", index=True)
