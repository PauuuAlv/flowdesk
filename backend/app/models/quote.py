from sqlalchemy import Column, Date, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.models.base import BaseModel, TenantMixin


class Quote(BaseModel, TenantMixin):
    __tablename__="quotes"
    __table_args__=(UniqueConstraint("tenant_id","sequence",name="uq_quote_tenant_sequence"),)
    sequence=Column(Integer,nullable=False)
    prefix=Column(String(12),nullable=False,default="COT")
    client_id=Column(UUID(as_uuid=True),ForeignKey("clients.id"),nullable=False,index=True)
    opportunity_id=Column(UUID(as_uuid=True),ForeignKey("opportunities.id"),nullable=True,index=True)
    owner_user_id=Column(UUID(as_uuid=True),ForeignKey("users.id"),nullable=False,index=True)
    issue_date=Column(Date,nullable=False)
    valid_until=Column(Date,nullable=False,index=True)
    currency=Column(String(3),nullable=False,default="MXN")
    discount=Column(Numeric(14,2),nullable=False,default=0)
    tax_rate=Column(Numeric(5,2),nullable=False,default=16)
    subtotal=Column(Numeric(14,2),nullable=False,default=0)
    tax=Column(Numeric(14,2),nullable=False,default=0)
    total=Column(Numeric(14,2),nullable=False,default=0)
    status=Column(String(20),nullable=False,default="draft",index=True)
    notes=Column(Text,nullable=True)
    client=relationship("Client",lazy="joined")
    opportunity=relationship("Opportunity",lazy="joined")
    owner=relationship("User",lazy="joined")
    items=relationship("QuoteItem",cascade="all, delete-orphan",lazy="joined",order_by="QuoteItem.position")


class QuoteItem(BaseModel):
    __tablename__="quote_items"
    quote_id=Column(UUID(as_uuid=True),ForeignKey("quotes.id",ondelete="CASCADE"),nullable=False,index=True)
    product_id=Column(UUID(as_uuid=True),ForeignKey("products.id"),nullable=True,index=True)
    position=Column(Integer,nullable=False)
    description=Column(String(240),nullable=False)
    quantity=Column(Numeric(12,2),nullable=False)
    unit_price=Column(Numeric(14,2),nullable=False)
    amount=Column(Numeric(14,2),nullable=False)
    product=relationship("Product",lazy="joined")
