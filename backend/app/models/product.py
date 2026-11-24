from sqlalchemy import Column, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import BaseModel, TenantMixin


class Product(BaseModel, TenantMixin):
    __tablename__ = "products"
    __table_args__ = (UniqueConstraint("tenant_id", "sku", name="uq_product_tenant_sku"),)

    name = Column(String(140), nullable=False, index=True)
    sku = Column(String(50), nullable=False, index=True)
    description = Column(Text, nullable=True)
    # Categoría del catálogo de la empresa (product_categories); es opcional.
    category_id = Column(UUID(as_uuid=True), ForeignKey("product_categories.id"), nullable=True, index=True)
    item_type = Column(String(20), nullable=False, default="service", index=True)
    unit = Column(String(30), nullable=False, default="service")
    unit_id = Column(UUID(as_uuid=True), ForeignKey("measurement_units.id"), nullable=False, index=True)
    brand_id = Column(UUID(as_uuid=True), ForeignKey("brands.id"), nullable=True, index=True)
    base_price = Column(Numeric(14, 2), nullable=False, default=0)
    # Moneda del precio (MXN, USD); por defecto la de la empresa al crearlo.
    currency = Column(String(3), nullable=False, default="MXN", server_default="MXN")
    tax_rate = Column(Numeric(5, 2), nullable=False, default=16)
    status = Column(String(20), nullable=False, default="active", index=True)

    measurement_unit = relationship("MeasurementUnit", lazy="joined")
    brand = relationship("Brand", lazy="joined")
    category = relationship("ProductCategory", lazy="joined")
