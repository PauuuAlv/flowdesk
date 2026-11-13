import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.security.permissions import require_permission
from app.models.activity import Activity
from app.models.client import Client
from app.models.opportunity import Opportunity
from app.models.user import User
from app.schemas.activity import ActivityResponse, SaveActivityRequest, UpdateActivityStatusRequest

router = APIRouter()


def _get(activity_id: uuid.UUID, tenant_id, db: Session) -> Activity:
    item = db.query(Activity).filter(Activity.id == activity_id, Activity.tenant_id == tenant_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Activity not found")
    return item


def _relations(payload: SaveActivityRequest, tenant_id, db: Session):
    try:
        client_id = uuid.UUID(payload.client_id)
        owner_id = uuid.UUID(payload.owner_user_id)
        opportunity_id = uuid.UUID(payload.opportunity_id) if payload.opportunity_id else None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid identifier") from exc
    client = db.query(Client).filter(Client.id == client_id, Client.tenant_id == tenant_id).first()
    owner = db.query(User).filter(User.id == owner_id, User.tenant_id == tenant_id, User.status == "active").first()
    opportunity = None
    if opportunity_id:
        opportunity = db.query(Opportunity).filter(Opportunity.id == opportunity_id, Opportunity.tenant_id == tenant_id).first()
        if opportunity and opportunity.client_id != client_id:
            raise HTTPException(status_code=409, detail="Opportunity does not belong to client")
    if not client: raise HTTPException(status_code=404, detail="Client not found")
    if not owner: raise HTTPException(status_code=404, detail="Owner not found")
    if opportunity_id and not opportunity: raise HTTPException(status_code=404, detail="Opportunity not found")
    return client, owner, opportunity


def _serialize(item: Activity) -> ActivityResponse:
    return ActivityResponse(id=str(item.id),client_id=str(item.client_id),client_name=item.client.company_name,
        opportunity_id=str(item.opportunity_id) if item.opportunity_id else None,
        opportunity_name=item.opportunity.name if item.opportunity else None,owner_user_id=str(item.owner_user_id),
        owner_name=item.owner.full_name or item.owner.email,activity_type=item.activity_type,title=item.title,
        description=item.description,scheduled_at=item.scheduled_at,status=item.status,completed_at=item.completed_at,
        created_at=item.created_at,updated_at=item.updated_at)


@router.get("", response_model=list[ActivityResponse])
def list_activities(db: Session=Depends(get_db), current_user: User=Depends(require_permission("activities.view"))):
    items=db.query(Activity).filter(Activity.tenant_id==current_user.tenant_id).order_by(Activity.scheduled_at.asc()).all()
    return [_serialize(item) for item in items]


@router.post("", response_model=ActivityResponse, status_code=status.HTTP_201_CREATED)
def create_activity(payload: SaveActivityRequest, db: Session=Depends(get_db), current_user: User=Depends(require_permission("activities.create"))):
    client,owner,opportunity=_relations(payload,current_user.tenant_id,db)
    item=Activity(tenant_id=current_user.tenant_id,client_id=client.id,owner_user_id=owner.id,
        opportunity_id=opportunity.id if opportunity else None,**payload.model_dump(exclude={"client_id","owner_user_id","opportunity_id"}))
    db.add(item);db.commit();db.refresh(item);return _serialize(item)


@router.get("/{activity_id}", response_model=ActivityResponse)
def get_activity(activity_id:uuid.UUID,db:Session=Depends(get_db),current_user:User=Depends(require_permission("activities.view"))):
    return _serialize(_get(activity_id,current_user.tenant_id,db))


@router.patch("/{activity_id}", response_model=ActivityResponse)
def update_activity(activity_id:uuid.UUID,payload:SaveActivityRequest,db:Session=Depends(get_db),current_user:User=Depends(require_permission("activities.update"))):
    item=_get(activity_id,current_user.tenant_id,db);client,owner,opportunity=_relations(payload,current_user.tenant_id,db)
    for key,value in payload.model_dump(exclude={"client_id","owner_user_id","opportunity_id"}).items():setattr(item,key,value)
    item.client_id=client.id;item.owner_user_id=owner.id;item.opportunity_id=opportunity.id if opportunity else None
    db.commit();db.refresh(item);return _serialize(item)


@router.patch("/{activity_id}/status", response_model=ActivityResponse)
def update_activity_status(activity_id:uuid.UUID,payload:UpdateActivityStatusRequest,db:Session=Depends(get_db),current_user:User=Depends(require_permission("activities.complete"))):
    item=_get(activity_id,current_user.tenant_id,db);item.status=payload.status
    item.completed_at=datetime.now(timezone.utc) if payload.status=="completed" else None
    db.commit();db.refresh(item);return _serialize(item)
