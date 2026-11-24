import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.opportunity import Opportunity
from app.models.opportunity_stage import OpportunityStage
from app.models.user import User
from app.schemas.opportunity_stage import (
    CreateOpportunityStageRequest,
    OpportunityStageResponse,
    UpdateOpportunityStageRequest,
)
from app.security.permissions import require_permission
from app.services.pipelines import MAX_STAGES_PER_PIPELINE, default_stage_color, pipeline_or_404, unique_stage_key

router = APIRouter()


def _serialize(item: OpportunityStage) -> OpportunityStageResponse:
    return OpportunityStageResponse(
        id=str(item.id), pipeline_id=str(item.pipeline_id), key=item.key, name=item.name,
        stage_type=item.stage_type, default_probability=item.default_probability,
        position=item.position, color=item.color, is_active=item.is_active, created_at=item.created_at,
    )


def _ensure_unique_name(db: Session, pipeline_id, name: str, exclude_id=None) -> None:
    """El nombre se repite libremente entre pipelines, pero no dentro de uno."""
    query = db.query(OpportunityStage).filter(
        OpportunityStage.pipeline_id == pipeline_id, func.lower(OpportunityStage.name) == name.lower()
    )
    if exclude_id:
        query = query.filter(OpportunityStage.id != exclude_id)
    if query.first():
        raise HTTPException(status_code=409, detail="Opportunity stage already exists")


@router.get("", response_model=list[OpportunityStageResponse])
def list_stages(
    search: str = Query(default="", max_length=80),
    include_inactive: bool = False,
    pipeline_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("opportunities.view")),
):
    query = db.query(OpportunityStage).filter(OpportunityStage.tenant_id == current_user.tenant_id)
    if pipeline_id:
        query = query.filter(OpportunityStage.pipeline_id == pipeline_id)
    if not include_inactive:
        query = query.filter(OpportunityStage.is_active.is_(True))
    if search.strip():
        query = query.filter(OpportunityStage.name.ilike(f"%{search.strip()}%"))
    return [_serialize(item) for item in query.order_by(OpportunityStage.position, OpportunityStage.name).all()]


@router.post("", response_model=OpportunityStageResponse, status_code=status.HTTP_201_CREATED)
def create_stage(
    payload: CreateOpportunityStageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("opportunities.update")),
):
    tenant_id = current_user.tenant_id
    pipeline = pipeline_or_404(db, tenant_id, payload.pipeline_id)
    count = db.query(func.count(OpportunityStage.id)).filter(OpportunityStage.pipeline_id == pipeline.id).scalar() or 0
    if count >= MAX_STAGES_PER_PIPELINE:
        raise HTTPException(status_code=409, detail="Opportunity stage limit reached")
    _ensure_unique_name(db, pipeline.id, payload.name)
    item = OpportunityStage(
        tenant_id=tenant_id, pipeline_id=pipeline.id, key=unique_stage_key(db, tenant_id, payload.name),
        **payload.model_dump(exclude={"pipeline_id", "color"}),
        color=payload.color or default_stage_color(payload.stage_type, count),
    )
    db.add(item); db.commit(); db.refresh(item)
    return _serialize(item)


@router.patch("/{stage_id}", response_model=OpportunityStageResponse)
def update_stage(
    stage_id: uuid.UUID,
    payload: UpdateOpportunityStageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("opportunities.update")),
):
    item = db.query(OpportunityStage).filter(
        OpportunityStage.id == stage_id, OpportunityStage.tenant_id == current_user.tenant_id,
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="Opportunity stage not found")
    _ensure_unique_name(db, item.pipeline_id, payload.name, exclude_id=item.id)
    if not payload.is_active:
        active_opportunities = db.query(func.count(Opportunity.id)).filter(
            Opportunity.tenant_id == current_user.tenant_id,
            Opportunity.stage == item.key,
            Opportunity.archived_at.is_(None),
        ).scalar() or 0
        if active_opportunities:
            raise HTTPException(status_code=409, detail="Stage has active opportunities")
    # Una etapa no cambia de pipeline: solo sus datos.
    for field, value in payload.model_dump(exclude={"pipeline_id", "color"}).items():
        setattr(item, field, value)
    if payload.color:
        item.color = payload.color
    db.commit(); db.refresh(item)
    return _serialize(item)
