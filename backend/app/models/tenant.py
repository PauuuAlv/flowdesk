from sqlalchemy import Boolean, Column, Integer, Numeric, String, Text

from app.models.base import BaseModel


class Tenant(BaseModel):
    """Cada empresa cliente del CRM es un Tenant.
    NO hereda TenantMixin (no tiene sentido que un tenant tenga tenant_id de sí mismo)."""

    __tablename__ = "tenants"

    name = Column(String(255), nullable=False)
    slug = Column(String(100), nullable=False, unique=True, index=True)
    is_active = Column(Boolean, nullable=False, default=True)
    legal_name = Column(String(255), nullable=True)
    tax_id = Column(String(20), nullable=True)
    contact_email = Column(String(255), nullable=True)
    contact_phone = Column(String(30), nullable=True)
    website = Column(String(255), nullable=True)
    logo_url = Column(String(500), nullable=True)
    address_line = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    postal_code = Column(String(12), nullable=True)
    country = Column(String(80), nullable=False, default="México")
    currency = Column(String(3), nullable=False, default="MXN")
    default_tax_rate = Column(Numeric(5, 2), nullable=False, default=16)
    quote_validity_days = Column(Integer, nullable=False, default=15)
    quote_prefix = Column(String(12), nullable=False, default="COT")
    payment_instructions = Column(Text, nullable=True)
