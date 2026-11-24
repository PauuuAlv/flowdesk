from sqlalchemy import Boolean, Column, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import BaseModel, TenantMixin


class Contact(BaseModel, TenantMixin):
    """EPIC-006: personas específicas dentro de un cliente (RF-018 a RF-020)."""

    __tablename__ = "contacts"
    __table_args__ = (
        # Solo puede existir un contacto principal por cliente.
        Index(
            "uq_contacts_primary_per_client",
            "client_id",
            unique=True,
            postgresql_where=text("is_primary"),
        ),
    )

    client_id = Column(
        UUID(as_uuid=True),
        ForeignKey("clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    full_name = Column(String(120), nullable=False)
    job_title = Column(String(120), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(30), nullable=True)
    is_primary = Column(Boolean, nullable=False, default=False)

    client = relationship("Client", lazy="joined")
