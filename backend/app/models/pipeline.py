from sqlalchemy import Boolean, Column, Index, Integer, String, UniqueConstraint, text

from app.models.base import BaseModel, TenantMixin


class Pipeline(BaseModel, TenantMixin):
    """Embudo de ventas de una empresa (RF-021/022). Cada uno tiene sus propias
    etapas (opportunity_stages.pipeline_id) y cada oportunidad pertenece a uno.
    Toda empresa tiene exactamente un pipeline predeterminado."""

    __tablename__ = "pipelines"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_pipeline_tenant_name"),
        Index(
            "uq_pipeline_tenant_default", "tenant_id", unique=True,
            postgresql_where=text("is_default"),
        ),
    )

    name = Column(String(80), nullable=False)
    description = Column(String(200), nullable=True)
    position = Column(Integer, nullable=False, default=1)
    is_default = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
