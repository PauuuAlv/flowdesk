from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.client import Client
from app.models.product import Product
from app.models.tenant import Tenant
from app.models.user import User

RESOURCE_CONFIG = {
    "users": (User, "max_users"),
    "clients": (Client, "max_clients"),
    "products": (Product, "max_products"),
}


def ensure_tenant_capacity(db: Session, tenant_id, resource: str) -> None:
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant or not tenant.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant subscription inactive")
    model, limit_field = RESOURCE_CONFIG[resource]
    current = db.query(func.count(model.id)).filter(model.tenant_id == tenant_id).scalar() or 0
    limit = getattr(tenant, limit_field)
    if current >= limit:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "PLAN_LIMIT_REACHED", "resource": resource, "limit": limit},
        )
