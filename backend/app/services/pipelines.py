"""Pipelines de oportunidades: creación con sus etapas y claves únicas."""

import re
import unicodedata
import uuid

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.opportunity_stage import OpportunityStage
from app.models.pipeline import Pipeline

# (clave, nombre, posición, tipo, probabilidad) de las etapas de un pipeline nuevo.
DEFAULT_STAGE_TEMPLATES = (
    ("prospecting", "Prospecto", 1, "normal", 10),
    ("contact", "Contacto", 2, "normal", 30),
    ("proposal", "Propuesta", 3, "normal", 60),
    ("negotiation", "Negociación", 4, "normal", 80),
    ("won", "Ganada", 5, "won", 100),
    ("lost", "Perdida", 6, "lost", 0),
)
DEFAULT_PIPELINE_NAME = "Ventas"
# Colores predeterminados: las etapas abiertas rotan por la paleta; Ganada y Perdida
# usan verde y rojo para reconocerlas de inmediato.
STAGE_PALETTE = ("#3b82f6", "#06b6d4", "#8b5cf6", "#f59e0b", "#ec4899", "#14b8a6", "#6366f1", "#f97316")
WON_COLOR, LOST_COLOR = "#22c55e", "#ef4444"


def default_stage_color(stage_type: str, index: int) -> str:
    if stage_type == "won":
        return WON_COLOR
    if stage_type == "lost":
        return LOST_COLOR
    return STAGE_PALETTE[index % len(STAGE_PALETTE)]


MAX_PIPELINES_PER_TENANT = 10
MAX_STAGES_PER_PIPELINE = 20


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value)
    ascii_value = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-")[:44] or "etapa"


def unique_stage_key(db: Session, tenant_id, base: str, reserved: set[str] | None = None) -> str:
    """Las claves de etapa son únicas por empresa (las usan Opportunity.stage y el
    historial). Si ya existe, se agrega un sufijo: prospecto, prospecto-2, …"""
    taken = {key for (key,) in db.query(OpportunityStage.key).filter(OpportunityStage.tenant_id == tenant_id)}
    taken |= reserved or set()
    base = slugify(base)
    key, n = base, 2
    while key in taken:
        key, n = f"{base}-{n}", n + 1
    return key


def default_pipeline(db: Session, tenant_id) -> Pipeline:
    pipeline = db.query(Pipeline).filter(Pipeline.tenant_id == tenant_id, Pipeline.is_default.is_(True)).first()
    if not pipeline:
        raise HTTPException(status_code=409, detail="The company has no default pipeline")
    return pipeline


def pipeline_or_404(db: Session, tenant_id, pipeline_id, active_only: bool = False) -> Pipeline:
    try:
        pipeline_uuid = pipeline_id if isinstance(pipeline_id, uuid.UUID) else uuid.UUID(str(pipeline_id))
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid pipeline id")
    query = db.query(Pipeline).filter(Pipeline.id == pipeline_uuid, Pipeline.tenant_id == tenant_id)
    if active_only:
        query = query.filter(Pipeline.is_active.is_(True))
    pipeline = query.first()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return pipeline


def create_pipeline(
    db: Session, tenant_id, *, name: str, description: str | None = None,
    is_default: bool = False, source: Pipeline | None = None,
) -> Pipeline:
    """Crea el pipeline con sus etapas: copia las de `source` o, si no hay, usa
    las predeterminadas (incluidas Ganada y Perdida para poder cerrar). No hace commit."""
    position = (db.query(Pipeline).filter(Pipeline.tenant_id == tenant_id).count() or 0) + 1
    pipeline = Pipeline(
        tenant_id=tenant_id, name=name, description=description,
        position=position, is_default=is_default, is_active=True,
    )
    db.add(pipeline)
    db.flush()

    if source:
        templates = [
            (stage.key, stage.name, stage.position, stage.stage_type, stage.default_probability, stage.color)
            for stage in db.query(OpportunityStage).filter(
                OpportunityStage.pipeline_id == source.id, OpportunityStage.is_active.is_(True)
            ).order_by(OpportunityStage.position)
        ]
    else:
        templates = [
            (*template, default_stage_color(template[3], i)) for i, template in enumerate(DEFAULT_STAGE_TEMPLATES)
        ]

    reserved: set[str] = set()
    for base_key, stage_name, stage_position, stage_type, probability, color in templates:
        key = unique_stage_key(db, tenant_id, base_key, reserved)
        reserved.add(key)
        db.add(OpportunityStage(
            tenant_id=tenant_id, pipeline_id=pipeline.id, key=key, name=stage_name,
            position=stage_position, stage_type=stage_type,
            default_probability=probability, color=color, is_active=True,
        ))
    db.flush()
    return pipeline
