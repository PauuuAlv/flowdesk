from sqlalchemy import Boolean, Column, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base import Base, BaseModel, TenantMixin


class Role(BaseModel, TenantMixin):
    __tablename__ = "roles"
    __table_args__ = (UniqueConstraint("tenant_id", "name", name="uq_role_tenant_name"),)

    name = Column(String(50), nullable=False)
    description = Column(String(160), nullable=False)
    origin = Column(String(20), nullable=False, default="custom")
    template_key = Column(String(50), nullable=True)
    is_protected = Column(Boolean, nullable=False, default=False)

    permissions = relationship(
        "RolePermission", cascade="all, delete-orphan", lazy="selectin"
    )


class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_id = Column(
        UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )
    permission_code = Column(String(80), primary_key=True)
