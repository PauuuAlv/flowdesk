import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.client import Client
from app.models.user import User
from app.repositories.client_repository import ClientRepository
from app.schemas.client import (
    ClientResponse,
    CreateClientRequest,
    UpdateClientRequest,
    UpdateClientStatusRequest,
)
from app.security.permissions import require_permission

router = APIRouter()


def _serialize(client: Client) -> ClientResponse:
    return ClientResponse(
        id=str(client.id),
        company_name=client.company_name,
        contact_name=client.contact_name,
        email=client.email,
        phone=client.phone,
        status=client.status,
        notes=client.notes,
        created_at=client.created_at,
        updated_at=client.updated_at,
    )


def _client_or_404(repository: ClientRepository, tenant_id, client_id: uuid.UUID) -> Client:
    client = repository.get(tenant_id, client_id)
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    return client


@router.get("", response_model=list[ClientResponse])
def list_clients(
    search: str | None = Query(default=None, max_length=120),
    client_status: str | None = Query(default=None, alias="status", pattern="^(active|inactive)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("clients.view")),
):
    repository = ClientRepository(db)
    return [
        _serialize(client)
        for client in repository.list_filtered(
            current_user.tenant_id, search=search, status=client_status
        )
    ]


@router.post("", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
def create_client(
    payload: CreateClientRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("clients.create")),
):
    repository = ClientRepository(db)
    if repository.find_by_email(current_user.tenant_id, str(payload.email)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Client email already exists")
    client = Client(
        tenant_id=current_user.tenant_id,
        company_name=payload.company_name,
        contact_name=payload.contact_name,
        email=str(payload.email),
        phone=payload.phone,
        notes=payload.notes,
        status="active",
    )
    db.add(client)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Client email already exists")
    db.refresh(client)
    return _serialize(client)


@router.get("/{client_id}", response_model=ClientResponse)
def get_client(
    client_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("clients.view")),
):
    return _serialize(_client_or_404(ClientRepository(db), current_user.tenant_id, client_id))


@router.patch("/{client_id}", response_model=ClientResponse)
def update_client(
    client_id: uuid.UUID,
    payload: UpdateClientRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("clients.update")),
):
    repository = ClientRepository(db)
    client = _client_or_404(repository, current_user.tenant_id, client_id)
    duplicate = repository.find_by_email(current_user.tenant_id, str(payload.email))
    if duplicate and duplicate.id != client.id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Client email already exists")
    for field, value in payload.model_dump().items():
        setattr(client, field, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Client email already exists")
    db.refresh(client)
    return _serialize(client)


@router.patch("/{client_id}/status", response_model=ClientResponse)
def update_client_status(
    client_id: uuid.UUID,
    payload: UpdateClientStatusRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("clients.delete")),
):
    client = _client_or_404(ClientRepository(db), current_user.tenant_id, client_id)
    client.status = payload.status
    db.commit()
    db.refresh(client)
    return _serialize(client)
