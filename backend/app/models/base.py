import uuid
from sqlalchemy import Column, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class TimestampMixin:
    """Agrega created_at / updated_at automáticos a cualquier modelo."""
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class TenantMixin:
    """CRÍTICO: toda tabla que pertenezca a un tenant debe heredar esto.
    tenant_id SIEMPRE se resuelve desde el JWT en el middleware,
    nunca se debe aceptar como parámetro directo del cliente (ver Threat Model, sección 19)."""
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)


class BaseModel(Base, TimestampMixin):
    __abstract__ = True
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
