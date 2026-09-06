import uuid
from typing import Generic, TypeVar, Type

from sqlalchemy.orm import Session

from app.models.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class TenantScopedRepository(Generic[ModelType]):
    """US-005 AC-03: repository base que aplica el filtro de tenant automáticamente.

    Todo repository que maneje datos de un tenant (Customer, Deal, Ticket, etc.)
    debe heredar de aquí y NUNCA hacer db.query(Model).filter(...) sin pasar por
    estos métodos, para que sea imposible -por accidente- devolver filas de otro
    tenant. tenant_id se recibe siempre ya resuelto (por el middleware, nunca
    por parámetro del cliente).
    """

    model: Type[ModelType]

    def __init__(self, db: Session):
        self.db = db

    def _base_query(self, tenant_id: uuid.UUID):
        return self.db.query(self.model).filter(self.model.tenant_id == tenant_id)

    def get(self, tenant_id: uuid.UUID, id: uuid.UUID) -> ModelType | None:
        return self._base_query(tenant_id).filter(self.model.id == id).first()

    def list(self, tenant_id: uuid.UUID, skip: int = 0, limit: int = 100) -> list[ModelType]:
        return self._base_query(tenant_id).offset(skip).limit(limit).all()

    def create(self, tenant_id: uuid.UUID, **kwargs) -> ModelType:
        obj = self.model(tenant_id=tenant_id, **kwargs)
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj
