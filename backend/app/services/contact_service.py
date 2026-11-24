"""Lógica de negocio de contactos (EPIC-006).

Reglas:
- Un cliente con contactos siempre tiene exactamente un contacto principal.
- El primer contacto de un cliente se vuelve principal automáticamente.
- Marcar un contacto como principal desmarca al anterior.
- Al borrar el principal se promueve el contacto más antiguo restante.
- clients.contact_name refleja siempre el nombre del contacto principal,
  para que listados, cotizaciones y PDF existentes sigan funcionando.
"""

import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.client import Client
from app.models.contact import Contact
from app.repositories.client_repository import ClientRepository
from app.repositories.contact_repository import ContactRepository
from app.schemas.contact import CreateContactRequest, UpdateContactRequest


class ContactService:
    def __init__(self, db: Session):
        self.db = db
        self.clients = ClientRepository(db)
        self.contacts = ContactRepository(db)

    def _client_or_404(self, tenant_id: uuid.UUID, client_id: uuid.UUID) -> Client:
        client = self.clients.get(tenant_id, client_id)
        if not client:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
        return client

    def _contact_or_404(self, tenant_id: uuid.UUID, client_id: uuid.UUID, contact_id: uuid.UUID) -> Contact:
        contact = self.contacts.get_for_client(tenant_id, client_id, contact_id)
        if not contact:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
        return contact

    def _make_primary(self, tenant_id: uuid.UUID, client: Client, contact: Contact) -> None:
        if not contact.is_primary:
            self.contacts.clear_primary(tenant_id, client.id)
            contact.is_primary = True
        client.contact_name = contact.full_name

    def list(self, tenant_id: uuid.UUID, client_id: uuid.UUID) -> list[Contact]:
        self._client_or_404(tenant_id, client_id)
        return self.contacts.list_for_client(tenant_id, client_id)

    def create(self, tenant_id: uuid.UUID, client_id: uuid.UUID, payload: CreateContactRequest) -> Contact:
        client = self._client_or_404(tenant_id, client_id)
        is_first = self.contacts.count_for_client(tenant_id, client_id) == 0
        contact = Contact(
            tenant_id=tenant_id,
            client_id=client.id,
            full_name=payload.full_name,
            job_title=payload.job_title,
            email=str(payload.email) if payload.email else None,
            phone=payload.phone,
            is_primary=False,
        )
        self.db.add(contact)
        self.db.flush()
        if is_first or payload.is_primary:
            self._make_primary(tenant_id, client, contact)
        self.db.commit()
        self.db.refresh(contact)
        return contact

    def update(
        self,
        tenant_id: uuid.UUID,
        client_id: uuid.UUID,
        contact_id: uuid.UUID,
        payload: UpdateContactRequest,
    ) -> Contact:
        client = self._client_or_404(tenant_id, client_id)
        contact = self._contact_or_404(tenant_id, client_id, contact_id)
        contact.full_name = payload.full_name
        contact.job_title = payload.job_title
        contact.email = str(payload.email) if payload.email else None
        contact.phone = payload.phone
        # El principal no se puede "desmarcar": hay que elegir otro como principal.
        if payload.is_primary or contact.is_primary:
            self._make_primary(tenant_id, client, contact)
        self.db.commit()
        self.db.refresh(contact)
        return contact

    def set_primary(self, tenant_id: uuid.UUID, client_id: uuid.UUID, contact_id: uuid.UUID) -> Contact:
        client = self._client_or_404(tenant_id, client_id)
        contact = self._contact_or_404(tenant_id, client_id, contact_id)
        self._make_primary(tenant_id, client, contact)
        self.db.commit()
        self.db.refresh(contact)
        return contact

    def delete(self, tenant_id: uuid.UUID, client_id: uuid.UUID, contact_id: uuid.UUID) -> None:
        client = self._client_or_404(tenant_id, client_id)
        contact = self._contact_or_404(tenant_id, client_id, contact_id)
        was_primary = contact.is_primary
        self.db.delete(contact)
        self.db.flush()
        if was_primary:
            remaining = sorted(
                self.contacts.list_for_client(tenant_id, client_id),
                key=lambda item: item.created_at,
            )
            if remaining:
                self._make_primary(tenant_id, client, remaining[0])
        self.db.commit()

    def sync_primary_from_client(self, tenant_id: uuid.UUID, client: Client) -> None:
        """Mantiene el contacto principal alineado con el formulario de cliente.

        Si el cliente aún no tiene contactos, crea el principal con los datos
        del cliente. No hace commit: lo hace quien llama.
        """
        primary = self.contacts.get_primary(tenant_id, client.id)
        if primary:
            primary.full_name = client.contact_name
            return
        self.db.add(
            Contact(
                tenant_id=tenant_id,
                client_id=client.id,
                full_name=client.contact_name,
                email=client.email,
                phone=client.phone,
                is_primary=True,
            )
        )
