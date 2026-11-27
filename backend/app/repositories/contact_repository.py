import uuid

from sqlalchemy.orm import Session

from app.models.contact import Contact
from app.repositories.base import TenantScopedRepository


class ContactRepository(TenantScopedRepository[Contact]):
    model = Contact

    def __init__(self, db: Session):
        super().__init__(db)

    def list_for_client(self, tenant_id: uuid.UUID, client_id: uuid.UUID) -> list[Contact]:
        return (
            self._base_query(tenant_id)
            .filter(Contact.client_id == client_id)
            .order_by(Contact.is_primary.desc(), Contact.full_name.asc())
            .all()
        )

    def get_for_client(
        self, tenant_id: uuid.UUID, client_id: uuid.UUID, contact_id: uuid.UUID
    ) -> Contact | None:
        return (
            self._base_query(tenant_id)
            .filter(Contact.client_id == client_id, Contact.id == contact_id)
            .first()
        )

    def get_primary(self, tenant_id: uuid.UUID, client_id: uuid.UUID) -> Contact | None:
        return (
            self._base_query(tenant_id)
            .filter(Contact.client_id == client_id, Contact.is_primary.is_(True))
            .first()
        )

    def count_for_client(self, tenant_id: uuid.UUID, client_id: uuid.UUID) -> int:
        return self._base_query(tenant_id).filter(Contact.client_id == client_id).count()

    def clear_primary(self, tenant_id: uuid.UUID, client_id: uuid.UUID) -> None:
        # Registro por registro (y no un UPDATE masivo) para que quede auditado.
        for contact in (
            self._base_query(tenant_id)
            .filter(Contact.client_id == client_id, Contact.is_primary.is_(True))
            .all()
        ):
            contact.is_primary = False
        # Se aplica antes de marcar el nuevo principal para no violar el índice único.
        self.db.flush()
