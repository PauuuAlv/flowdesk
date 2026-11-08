from sqlalchemy import Column, String, Text, UniqueConstraint

from app.models.base import BaseModel, TenantMixin


class Client(BaseModel, TenantMixin):
    __tablename__ = "clients"
    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_client_tenant_email"),
    )

    company_name = Column(String(120), nullable=False, index=True)
    contact_name = Column(String(120), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    phone = Column(String(30), nullable=True)
    status = Column(String(20), nullable=False, default="active", index=True)
    notes = Column(Text, nullable=True)
