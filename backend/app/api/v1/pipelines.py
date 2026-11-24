"""Pipelines de oportunidades (RF-021/022): cada empresa puede tener varios."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.opportunity import Opportunity
from app.models.opportunity_stage import OpportunityStage
from app.models.pipeline import Pipeline
from app.models.user import User
from app.schemas.pipeline import CreatePipelineRequest, PipelineResponse, UpdatePipelineRequest
from app.security.permissions import require_permission
from app.services.pipelines import MAX_PIPELINES_PER_TENANT, create_pipeline, pipeline_or_404

router = APIRouter()


def _serialize(db: Session, item: Pipeline) -> PipelineResponse:
    stage_count = db.query(func.count(OpportunityStage.id)).filter(
        OpportunityStage.pipeline_id == item.id, OpportunityStage.is_active.is_(True)
    ).scalar() or 0
    total = db.query(func.count(Opportunity.id)).filter(Opportunity.pipeline_id == item.id).scalar() or 0
    open_count = db.query(func.count(Opportunity.id)).filter(
        Opportunity.pipeline_id == item.id,
        Opportunity.archived_at.is_(None),
        Opportunity.closed_at.is_(None),
    ).scalar() or 0
    return PipelineResponse(
        id=str(item.id), name=item.name, description=item.description, position=item.position,
        is_default=item.is_default, is_active=item.is_active, stage_count=stage_count,
        open_opportunities=open_count, total_opportunities=total, created_at=item.created_at,
    )


def _ensure_unique_name(db: Session, tenant_id, name: str, exclude_id=None) -> None:
    query = db.query(Pipeline).filter(Pipeline.tenant_id == tenant_id, func.lower(Pipeline.name) == name.lower())
    if exclude_id:
        query = query.filter(Pipeline.id != exclude_id)
    if query.first():
        raise HTTPException(status_code=409, detail="Pipeline name already exists")


@router.get("", response_model=list[PipelineResponse])
def list_pipelines(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("opportunities.view")),
):
    query = db.query(Pipeline).filter(Pipeline.tenant_id == current_user.tenant_id)
    if not include_inactive:
        query = query.filter(Pipeline.is_active.is_(True))
    items = query.order_by(Pipeline.is_default.desc(), Pipeline.position, Pipeline.name).all()
    return [_serialize(db, item) for item in items]


@router.post("", response_model=PipelineResponse, status_code=status.HTTP_201_CREATED)
def create(
    payload: CreatePipelineRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("opportunities.update")),
):
    tenant_id = current_user.tenant_id
    count = db.query(func.count(Pipeline.id)).filter(Pipeline.tenant_id == tenant_id).scalar() or 0
    if count >= MAX_PIPELINES_PER_TENANT:
        raise HTTPException(status_code=409, detail="Pipeline limit reached")
    _ensure_unique_name(db, tenant_id, payload.name)
    source = pipeline_or_404(db, tenant_id, payload.copy_stages_from) if payload.copy_stages_from else None
    item = create_pipeline(db, tenant_id, name=payload.name, description=payload.description, source=source)
    db.commit(); db.refresh(item)
    return _serialize(db, item)


@router.patch("/{pipeline_id}", response_model=PipelineResponse)
def update(
    pipeline_id: uuid.UUID,
    payload: UpdatePipelineRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("opportunities.update")),
):
    tenant_id = current_user.tenant_id
    item = pipeline_or_404(db, tenant_id, pipeline_id)
    _ensure_unique_name(db, tenant_id, payload.name, exclude_id=item.id)

    # El predeterminado siempre está activo; se cambia marcando otro como predeterminado.
    if item.is_default and not payload.is_default:
        raise HTTPException(status_code=409, detail="Mark another pipeline as default instead")
    if payload.is_default and not payload.is_active:
        raise HTTPException(status_code=409, detail="The default pipeline must be active")
    if not payload.is_active and item.is_active:
        open_count = db.query(func.count(Opportunity.id)).filter(
            Opportunity.pipeline_id == item.id,
            Opportunity.archived_at.is_(None),
            Opportunity.closed_at.is_(None),
        ).scalar() or 0
        if open_count:
            raise HTTPException(status_code=409, detail="Pipeline has open opportunities")

    if payload.is_default and not item.is_default:
        db.query(Pipeline).filter(Pipeline.tenant_id == tenant_id, Pipeline.is_default.is_(True)).update(
            {Pipeline.is_default: False}, synchronize_session=False
        )
        db.flush()
    item.name, item.description = payload.name, payload.description
    item.is_active, item.is_default = payload.is_active, payload.is_default
    db.commit(); db.refresh(item)
    return _serialize(db, item)


@router.delete("/{pipeline_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(
    pipeline_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("opportunities.update")),
):
    item = pipeline_or_404(db, current_user.tenant_id, pipeline_id)
    if item.is_default:
        raise HTTPException(status_code=409, detail="The default pipeline cannot be deleted")
    if db.query(Opportunity.id).filter(Opportunity.pipeline_id == item.id).first():
        raise HTTPException(status_code=409, detail="Pipeline has opportunities")
    db.query(OpportunityStage).filter(OpportunityStage.pipeline_id == item.id).delete(synchronize_session=False)
    db.delete(item)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
