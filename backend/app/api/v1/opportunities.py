import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.client import Client
from app.models.opportunity import Opportunity
from app.models.user import User
from app.schemas.opportunity import (
    OpportunityAssigneeResponse,
    CloseOpportunityRequest,
    OpportunityResponse,
    SaveOpportunityRequest,
    UpdateOpportunityStageRequest,
)
from app.security.permissions import require_permission

router = APIRouter()


def _opportunity_or_404(db: Session, tenant_id, opportunity_id: uuid.UUID) -> Opportunity:
    item = db.query(Opportunity).filter(Opportunity.id == opportunity_id, Opportunity.tenant_id == tenant_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return item


def _related_or_404(db: Session, tenant_id, client_id: str, owner_id: str):
    try:
        client_uuid, owner_uuid = uuid.UUID(client_id), uuid.UUID(owner_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid related id")
    client = db.query(Client).filter(Client.id == client_uuid, Client.tenant_id == tenant_id).first()
    owner = db.query(User).filter(User.id == owner_uuid, User.tenant_id == tenant_id, User.status == "active").first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")
    return client, owner


def _serialize(item: Opportunity) -> OpportunityResponse:
    return OpportunityResponse(
        id=str(item.id), client_id=str(item.client_id), client_name=item.client.company_name,
        owner_user_id=str(item.owner_user_id), owner_name=item.owner.full_name or item.owner.email,
        name=item.name, amount=item.amount, stage=item.stage, probability=item.probability,
        expected_close_date=item.expected_close_date, notes=item.notes,
        loss_reason=item.loss_reason, loss_detail=item.loss_detail, archived=item.archived_at is not None,
        created_at=item.created_at, updated_at=item.updated_at,
    )


@router.get("", response_model=list[OpportunityResponse])
def list_opportunities(include_archived: bool = False, db: Session = Depends(get_db), current_user: User = Depends(require_permission("opportunities.view"))):
    query = db.query(Opportunity).filter(Opportunity.tenant_id == current_user.tenant_id)
    if not include_archived:
        query = query.filter(Opportunity.archived_at.is_(None))
    items = query.order_by(Opportunity.updated_at.desc()).all()
    return [_serialize(item) for item in items]


@router.get("/assignees", response_model=list[OpportunityAssigneeResponse])
def list_assignees(db: Session = Depends(get_db), current_user: User = Depends(require_permission("opportunities.view"))):
    users = db.query(User).filter(User.tenant_id == current_user.tenant_id, User.status == "active").order_by(User.full_name.asc()).all()
    return [OpportunityAssigneeResponse(id=str(user.id), name=user.full_name or user.email) for user in users]


@router.post("", response_model=OpportunityResponse, status_code=status.HTTP_201_CREATED)
def create_opportunity(payload: SaveOpportunityRequest, db: Session = Depends(get_db), current_user: User = Depends(require_permission("opportunities.create"))):
    client, owner = _related_or_404(db, current_user.tenant_id, payload.client_id, payload.owner_user_id)
    item = Opportunity(tenant_id=current_user.tenant_id, client_id=client.id, owner_user_id=owner.id, **payload.model_dump(exclude={"client_id", "owner_user_id"}))
    db.add(item); db.commit(); db.refresh(item)
    return _serialize(item)


@router.get("/{opportunity_id}", response_model=OpportunityResponse)
def get_opportunity(opportunity_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(require_permission("opportunities.view"))):
    return _serialize(_opportunity_or_404(db, current_user.tenant_id, opportunity_id))


@router.patch("/{opportunity_id}", response_model=OpportunityResponse)
def update_opportunity(opportunity_id: uuid.UUID, payload: SaveOpportunityRequest, db: Session = Depends(get_db), current_user: User = Depends(require_permission("opportunities.update"))):
    item = _opportunity_or_404(db, current_user.tenant_id, opportunity_id)
    client, owner = _related_or_404(db, current_user.tenant_id, payload.client_id, payload.owner_user_id)
    for key, value in payload.model_dump(exclude={"client_id", "owner_user_id"}).items(): setattr(item, key, value)
    item.client_id, item.owner_user_id = client.id, owner.id
    db.commit(); db.refresh(item)
    return _serialize(item)


@router.patch("/{opportunity_id}/stage", response_model=OpportunityResponse)
def update_stage(opportunity_id: uuid.UUID, payload: UpdateOpportunityStageRequest, db: Session = Depends(get_db), current_user: User = Depends(require_permission("opportunities.update"))):
    item = _opportunity_or_404(db, current_user.tenant_id, opportunity_id)
    if payload.stage in ("won", "lost"):
        raise HTTPException(status_code=409, detail="Use the close opportunity endpoint")
    item.stage = payload.stage
    item.probability = 100 if payload.stage == "won" else 0 if payload.stage == "lost" else item.probability
    db.commit(); db.refresh(item)
    return _serialize(item)


@router.post("/{opportunity_id}/close", response_model=OpportunityResponse)
def close_opportunity(opportunity_id: uuid.UUID, payload: CloseOpportunityRequest, db: Session = Depends(get_db), current_user: User = Depends(require_permission("opportunities.close"))):
    item = _opportunity_or_404(db, current_user.tenant_id, opportunity_id)
    if payload.stage == "lost" and not payload.loss_reason:
        raise HTTPException(status_code=422, detail="Loss reason is required")
    item.stage = payload.stage
    item.probability = 100 if payload.stage == "won" else 0
    item.loss_reason = payload.loss_reason if payload.stage == "lost" else None
    item.loss_detail = payload.loss_detail.strip() if payload.loss_detail and payload.stage == "lost" else None
    db.commit(); db.refresh(item)
    return _serialize(item)


@router.post("/{opportunity_id}/archive", response_model=OpportunityResponse)
def archive_opportunity(opportunity_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(require_permission("opportunities.archive"))):
    from datetime import datetime, timezone
    item = _opportunity_or_404(db, current_user.tenant_id, opportunity_id)
    item.archived_at = datetime.now(timezone.utc)
    db.commit(); db.refresh(item)
    return _serialize(item)


@router.post("/{opportunity_id}/restore", response_model=OpportunityResponse)
def restore_opportunity(opportunity_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(require_permission("opportunities.archive"))):
    item = _opportunity_or_404(db, current_user.tenant_id, opportunity_id)
    item.archived_at = None
    db.commit(); db.refresh(item)
    return _serialize(item)
