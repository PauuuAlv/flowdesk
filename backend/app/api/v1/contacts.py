"""EPIC-006 Contacts: /api/clients/{client_id}/contacts.

Ver contactos requiere `clients.view`; crearlos, editarlos o borrarlos
requiere `clients.update`, porque forman parte de la ficha del cliente.
"""

import uuid

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.contact import Contact
from app.models.user import User
from app.schemas.contact import ContactResponse, CreateContactRequest, UpdateContactRequest
from app.security.permissions import require_permission
from app.services.contact_service import ContactService

router = APIRouter()


def _serialize(contact: Contact) -> ContactResponse:
    return ContactResponse(
        id=str(contact.id),
        client_id=str(contact.client_id),
        full_name=contact.full_name,
        job_title=contact.job_title,
        email=contact.email,
        phone=contact.phone,
        is_primary=contact.is_primary,
        created_at=contact.created_at,
        updated_at=contact.updated_at,
    )


@router.get("", response_model=list[ContactResponse])
def list_contacts(
    client_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("clients.view")),
):
    return [_serialize(item) for item in ContactService(db).list(current_user.tenant_id, client_id)]


@router.post("", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
def create_contact(
    client_id: uuid.UUID,
    payload: CreateContactRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("clients.update")),
):
    return _serialize(ContactService(db).create(current_user.tenant_id, client_id, payload))


@router.patch("/{contact_id}", response_model=ContactResponse)
def update_contact(
    client_id: uuid.UUID,
    contact_id: uuid.UUID,
    payload: UpdateContactRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("clients.update")),
):
    return _serialize(ContactService(db).update(current_user.tenant_id, client_id, contact_id, payload))


@router.post("/{contact_id}/primary", response_model=ContactResponse)
def set_primary_contact(
    client_id: uuid.UUID,
    contact_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("clients.update")),
):
    return _serialize(ContactService(db).set_primary(current_user.tenant_id, client_id, contact_id))


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contact(
    client_id: uuid.UUID,
    contact_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("clients.update")),
):
    ContactService(db).delete(current_user.tenant_id, client_id, contact_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
