from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import BaseModel, TenantMixin


class OpportunityStage(BaseModel, TenantMixin):
    __tablename__ = "opportunity_stages"
    __table_args__ = (
        # La clave sigue siendo única por empresa: Opportunity.stage y el historial la usan.
        UniqueConstraint("tenant_id", "key", name="uq_opportunity_stage_tenant_key"),
        # El nombre solo se repite entre pipelines distintos ("Prospecto" en varios).
        UniqueConstraint("pipeline_id", "name", name="uq_opportunity_stage_pipeline_name"),
    )

    pipeline_id = Column(UUID(as_uuid=True), ForeignKey("pipelines.id"), nullable=False, index=True)
    key = Column(String(50), nullable=False)
    name = Column(String(80), nullable=False)
    position = Column(Integer, nullable=False, default=1)
    stage_type = Column(String(20), nullable=False, default="normal")
    default_probability = Column(Integer, nullable=False, default=10)
    # Color base (hex #rrggbb); el tablero usa un tono suave de él como fondo de la columna.
    color = Column(String(7), nullable=False, default="#3b82f6", server_default="#3b82f6")
    is_active = Column(Boolean, nullable=False, default=True)
