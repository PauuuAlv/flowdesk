from sqlalchemy import Column, String, Boolean

from app.models.base import BaseModel


class Tenant(BaseModel):
    """Cada empresa cliente del CRM es un Tenant.
    NO hereda TenantMixin (no tiene sentido que un tenant tenga tenant_id de sí mismo)."""

    __tablename__ = "tenants"

    name = Column(String(255), nullable=False)
    slug = Column(String(100), nullable=False, unique=True, index=True)
    is_active = Column(Boolean, nullable=False, default=True)
