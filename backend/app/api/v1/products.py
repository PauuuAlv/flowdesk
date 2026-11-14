import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.product import Product
from app.models.user import User
from app.schemas.product import CreateProductRequest, ProductResponse, UpdateProductRequest, UpdateProductStatusRequest
from app.security.permissions import require_permission

router = APIRouter()


def _serialize(item: Product) -> ProductResponse:
    return ProductResponse(id=str(item.id), name=item.name, sku=item.sku, description=item.description,
        category=item.category, item_type=item.item_type, unit=item.unit, base_price=item.base_price,
        tax_rate=item.tax_rate, status=item.status, created_at=item.created_at, updated_at=item.updated_at)


def _get(product_id: uuid.UUID, tenant_id, db: Session) -> Product:
    item = db.query(Product).filter(Product.id == product_id, Product.tenant_id == tenant_id).first()
    if not item: raise HTTPException(status_code=404, detail="Product not found")
    return item


@router.get("", response_model=list[ProductResponse])
def list_products(search: str | None = Query(default=None, max_length=140), product_status: str | None = Query(default=None, alias="status", pattern="^(active|inactive)$"),
    item_type: str | None = Query(default=None, pattern="^(product|service)$"), db: Session = Depends(get_db), current_user: User = Depends(require_permission("products.view"))):
    query = db.query(Product).filter(Product.tenant_id == current_user.tenant_id)
    if search:
        term = f"%{search.strip()}%"
        query = query.filter(or_(Product.name.ilike(term), Product.sku.ilike(term), Product.category.ilike(term)))
    if product_status: query = query.filter(Product.status == product_status)
    if item_type: query = query.filter(Product.item_type == item_type)
    return [_serialize(item) for item in query.order_by(Product.name.asc()).all()]


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(payload: CreateProductRequest, db: Session = Depends(get_db), current_user: User = Depends(require_permission("products.create"))):
    item = Product(tenant_id=current_user.tenant_id, status="active", **payload.model_dump())
    db.add(item)
    try: db.commit()
    except IntegrityError:
        db.rollback(); raise HTTPException(status_code=409, detail="Product SKU already exists")
    db.refresh(item); return _serialize(item)


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(require_permission("products.view"))):
    return _serialize(_get(product_id, current_user.tenant_id, db))


@router.patch("/{product_id}", response_model=ProductResponse)
def update_product(product_id: uuid.UUID, payload: UpdateProductRequest, db: Session = Depends(get_db), current_user: User = Depends(require_permission("products.update"))):
    item = _get(product_id, current_user.tenant_id, db)
    for key, value in payload.model_dump().items(): setattr(item, key, value)
    try: db.commit()
    except IntegrityError:
        db.rollback(); raise HTTPException(status_code=409, detail="Product SKU already exists")
    db.refresh(item); return _serialize(item)


@router.patch("/{product_id}/status", response_model=ProductResponse)
def update_product_status(product_id: uuid.UUID, payload: UpdateProductStatusRequest, db: Session = Depends(get_db), current_user: User = Depends(require_permission("products.delete"))):
    item = _get(product_id, current_user.tenant_id, db); item.status = payload.status
    db.commit(); db.refresh(item); return _serialize(item)
