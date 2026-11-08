import uuid

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.client import Client
from app.repositories.base import TenantScopedRepository


class ClientRepository(TenantScopedRepository[Client]):
    model = Client

    def __init__(self, db: Session):
        super().__init__(db)

    def list_filtered(
        self,
        tenant_id: uuid.UUID,
        *,
        search: str | None = None,
        status: str | None = None,
    ) -> list[Client]:
        query = self._base_query(tenant_id)
        if search:
            term = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Client.company_name.ilike(term),
                    Client.contact_name.ilike(term),
                    Client.email.ilike(term),
                )
            )
        if status:
            query = query.filter(Client.status == status)
        return query.order_by(Client.company_name.asc()).all()

    def find_by_email(self, tenant_id: uuid.UUID, email: str) -> Client | None:
        return (
            self._base_query(tenant_id)
            .filter(Client.email == email.strip().lower())
            .first()
        )
