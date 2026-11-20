import re
import unicodedata
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

router = APIRouter()
MAX_STAGES_PER_TENANT = 20


def _serialize(item: OpportunityStage) -> OpportunityStageResponse:
    return OpportunityStageResponse(
        id=str(item.id), key=item.key, name=item.name, stage_type=item.stage_type,
        default_probability=item.default_probability, position=item.position,
        is_active=item.is_active, created_at=item.created_at,
    )


def _key(name: str) -> str:
    normalized = unicodedata.normalize("NFD", name)
    ascii_name = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")[:50]


@router.get("", response_model=list[OpportunityStageResponse])
def list_stages(
    search: str = Query(default="", max_length=80),
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("opportunities.view")),
):
    query = db.query(OpportunityStage).filter(OpportunityStage.tenant_id == current_user.tenant_id)
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
    count = db.query(func.count(OpportunityStage.id)).filter(OpportunityStage.tenant_id == current_user.tenant_id).scalar() or 0
    if count >= MAX_STAGES_PER_TENANT:
        raise HTTPException(status_code=409, detail="Opportunity stage limit reached")
    key = _key(payload.name)
    duplicate = db.query(OpportunityStage).filter(
        OpportunityStage.tenant_id == current_user.tenant_id,
        (OpportunityStage.key == key) | (func.lower(OpportunityStage.name) == payload.name.lower()),
    ).first()
    if duplicate:
        raise HTTPException(status_code=409, detail="Opportunity stage already exists")
    item = OpportunityStage(tenant_id=current_user.tenant_id, key=key, **payload.model_dump())
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
    duplicate = db.query(OpportunityStage).filter(
        OpportunityStage.tenant_id == current_user.tenant_id,
        func.lower(OpportunityStage.name) == payload.name.lower(),
        OpportunityStage.id != item.id,
    ).first()
    if duplicate:
        raise HTTPException(status_code=409, detail="Opportunity stage already exists")
    if not payload.is_active:
        active_opportunities = db.query(func.count(Opportunity.id)).filter(
            Opportunity.tenant_id == current_user.tenant_id,
            Opportunity.stage == item.key,
            Opportunity.archived_at.is_(None),
        ).scalar() or 0
        if active_opportunities:
            raise HTTPException(status_code=409, detail="Stage has active opportunities")
    for field, value in payload.model_dump().items():
        setattr(item, field, value)
    db.commit(); db.refresh(item)
    return _serialize(item)
