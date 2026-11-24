import re
import unicodedata
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.currencies import tenant_currency
from app.core.database import get_db
from app.models.product import Product
from app.models.product_catalog import Brand, MeasurementUnit, ProductCategory
from app.models.user import User
from app.schemas.product import CreateProductRequest, ProductResponse, UpdateProductRequest, UpdateProductStatusRequest
from app.security.permissions import require_permission
from app.services.saas_limits import ensure_tenant_capacity

router = APIRouter()


def _sku_base(name: str, item_type: str) -> str:
    normalized = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^A-Za-z0-9]+", "-", normalized.upper()).strip("-") or "ELEMENTO"
    prefix = "PRO" if item_type == "product" else "SER"
    return f"{prefix}-{slug}"[:50].rstrip("-")


def _next_available_sku(db: Session, tenant_id, name: str, item_type: str) -> str:
    base = _sku_base(name, item_type)
    candidate = base
    consecutive = 2
    while db.query(Product.id).filter(Product.tenant_id == tenant_id, Product.sku == candidate).first():
        suffix = f"-{consecutive:02d}"
        candidate = f"{base[:50 - len(suffix)].rstrip('-')}{suffix}"
        consecutive += 1
    return candidate


def _serialize(item: Product) -> ProductResponse:
    return ProductResponse(id=str(item.id), name=item.name, sku=item.sku, description=item.description,
        category_id=str(item.category_id) if item.category_id else None,
        category=item.category.name if item.category else None, item_type=item.item_type, unit=item.unit, unit_id=str(item.unit_id),
        unit_name=item.measurement_unit.name, unit_abbreviation=item.measurement_unit.abbreviation,
        brand_id=str(item.brand_id) if item.brand_id else None, brand_name=item.brand.name if item.brand else None,
        base_price=item.base_price, currency=item.currency,
        tax_rate=item.tax_rate, status=item.status, created_at=item.created_at, updated_at=item.updated_at)


def _get(product_id: uuid.UUID, tenant_id, db: Session) -> Product:
    item = db.query(Product).filter(Product.id == product_id, Product.tenant_id == tenant_id).first()
    if not item: raise HTTPException(status_code=404, detail="Product not found")
    return item


def _catalog_items(db: Session, tenant_id, unit_id: str, brand_id: str | None, item_type: str, allow_inactive: bool = False):
    try: unit_uuid = uuid.UUID(unit_id); brand_uuid = uuid.UUID(brand_id) if brand_id else None
    except ValueError: raise HTTPException(status_code=422, detail="Invalid catalog identifier")
    unit_query = db.query(MeasurementUnit).filter(MeasurementUnit.id == unit_uuid, MeasurementUnit.tenant_id == tenant_id)
    if not allow_inactive: unit_query = unit_query.filter(MeasurementUnit.is_active.is_(True))
    unit = unit_query.first()
    if not unit: raise HTTPException(status_code=404, detail="Measurement unit not found")
    # Un producto solo usa unidades de producto y un servicio, de servicio.
    if unit.item_type != item_type:
        raise HTTPException(status_code=422, detail={"code": "UNIT_TYPE_MISMATCH", "unit_type": unit.item_type})
    brand = None
    if brand_uuid:
        brand_query = db.query(Brand).filter(Brand.id == brand_uuid, Brand.tenant_id == tenant_id)
        if not allow_inactive: brand_query = brand_query.filter(Brand.is_active.is_(True))
        brand = brand_query.first()
        if not brand: raise HTTPException(status_code=404, detail="Brand not found")
    return unit, brand


def _category_or_none(db: Session, tenant_id, category_id: str | None, allow_inactive: bool = False):
    """Categoría del catálogo de la empresa; al editar se admite la actual aunque esté inactiva."""
    if not category_id:
        return None
    try: category_uuid = uuid.UUID(category_id)
    except ValueError: raise HTTPException(status_code=422, detail="Invalid catalog identifier")
    query = db.query(ProductCategory).filter(ProductCategory.id == category_uuid, ProductCategory.tenant_id == tenant_id)
    if not allow_inactive: query = query.filter(ProductCategory.is_active.is_(True))
    category = query.first()
    if not category: raise HTTPException(status_code=404, detail="Category not found")
    return category


@router.get("", response_model=list[ProductResponse])
def list_products(search: str | None = Query(default=None, max_length=140), product_status: str | None = Query(default=None, alias="status", pattern="^(active|inactive)$"),
    item_type: str | None = Query(default=None, pattern="^(product|service)$"), db: Session = Depends(get_db), current_user: User = Depends(require_permission("products.view"))):
    query = db.query(Product).filter(Product.tenant_id == current_user.tenant_id)
    if search:
        term = f"%{search.strip()}%"
        query = query.outerjoin(Brand).outerjoin(ProductCategory).filter(or_(Product.name.ilike(term), Product.sku.ilike(term), ProductCategory.name.ilike(term), Brand.name.ilike(term)))
    if product_status: query = query.filter(Product.status == product_status)
    if item_type: query = query.filter(Product.item_type == item_type)
    return [_serialize(item) for item in query.order_by(Product.name.asc()).all()]


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(payload: CreateProductRequest, db: Session = Depends(get_db), current_user: User = Depends(require_permission("products.create"))):
    ensure_tenant_capacity(db, current_user.tenant_id, "products")
    duplicate_name = db.query(Product).filter(
        Product.tenant_id == current_user.tenant_id,
        Product.item_type == payload.item_type,
        func.lower(Product.name) == payload.name.casefold(),
    ).first()
    if duplicate_name:
        raise HTTPException(status_code=409, detail={"code": "PRODUCT_NAME_EXISTS", "sku": duplicate_name.sku})
    unit, brand = _catalog_items(db, current_user.tenant_id, payload.unit_id, payload.brand_id, payload.item_type)
    category = _category_or_none(db, current_user.tenant_id, payload.category_id)
    values = payload.model_dump(exclude={"unit_id", "brand_id", "sku", "currency", "category_id"})
    values["category_id"] = category.id if category else None
    values["currency"] = payload.currency or tenant_currency(db, current_user.tenant_id)
    sku = _next_available_sku(db, current_user.tenant_id, payload.name, payload.item_type)
    item = Product(tenant_id=current_user.tenant_id, status="active", unit=unit.key, unit_id=unit.id, brand_id=brand.id if brand else None, sku=sku, **values)
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
    duplicate_name = db.query(Product).filter(
        Product.tenant_id == current_user.tenant_id,
        Product.id != item.id,
        Product.item_type == payload.item_type,
        func.lower(Product.name) == payload.name.casefold(),
    ).first()
    if duplicate_name:
        raise HTTPException(status_code=409, detail={"code": "PRODUCT_NAME_EXISTS", "sku": duplicate_name.sku})
    unit, brand = _catalog_items(db, current_user.tenant_id, payload.unit_id, payload.brand_id, payload.item_type, allow_inactive=True)
    category = _category_or_none(db, current_user.tenant_id, payload.category_id, allow_inactive=payload.category_id == (str(item.category_id) if item.category_id else None))
    for key, value in payload.model_dump(exclude={"unit_id", "brand_id", "currency", "category_id"}).items(): setattr(item, key, value)
    item.category_id = category.id if category else None
    if payload.currency: item.currency = payload.currency
    item.unit, item.unit_id, item.brand_id = unit.key, unit.id, brand.id if brand else None
    try: db.commit()
    except IntegrityError:
        db.rollback(); raise HTTPException(status_code=409, detail="Product SKU already exists")
    db.refresh(item); return _serialize(item)


@router.patch("/{product_id}/status", response_model=ProductResponse)
def update_product_status(product_id: uuid.UUID, payload: UpdateProductStatusRequest, db: Session = Depends(get_db), current_user: User = Depends(require_permission("products.delete"))):
    item = _get(product_id, current_user.tenant_id, db); item.status = payload.status
    db.commit(); db.refresh(item); return _serialize(item)
