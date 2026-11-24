import re
import unicodedata
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.product import Product
from app.models.product_catalog import Brand, MeasurementUnit, ProductCategory
from app.models.user import User
from app.schemas.product_catalog import (
    BrandResponse, CategoryResponse, CreateBrandRequest, CreateCategoryRequest, CreateUnitRequest,
    UnitResponse, UpdateBrandRequest, UpdateCategoryRequest, UpdateUnitRequest,
)
from app.security.permissions import require_permission

router = APIRouter()


def _key(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value)
    ascii_value = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    return re.sub(r"[^a-z0-9]+", "-", ascii_value.lower()).strip("-")[:50]


def _unit(item: MeasurementUnit) -> UnitResponse:
    return UnitResponse(id=str(item.id), key=item.key, name=item.name, abbreviation=item.abbreviation, item_type=item.item_type, is_active=item.is_active, created_at=item.created_at)


def _brand(item: Brand) -> BrandResponse:
    return BrandResponse(id=str(item.id), name=item.name, description=item.description, is_active=item.is_active, created_at=item.created_at)


@router.get("/units", response_model=list[UnitResponse])
def list_units(search: str = Query(default="", max_length=80), include_inactive: bool = False,
    item_type: str | None = Query(default=None, pattern="^(product|service)$"),
    db: Session = Depends(get_db), current_user: User = Depends(require_permission("products.view"))):
    query = db.query(MeasurementUnit).filter(MeasurementUnit.tenant_id == current_user.tenant_id)
    if not include_inactive: query = query.filter(MeasurementUnit.is_active.is_(True))
    if item_type: query = query.filter(MeasurementUnit.item_type == item_type)
    if search.strip(): query = query.filter(MeasurementUnit.name.ilike(f"%{search.strip()}%"))
    return [_unit(item) for item in query.order_by(MeasurementUnit.name).all()]


@router.post("/units", response_model=UnitResponse, status_code=status.HTTP_201_CREATED)
def create_unit(payload: CreateUnitRequest, db: Session = Depends(get_db), current_user: User = Depends(require_permission("products.update"))):
    key = _key(payload.name)
    if not key: raise HTTPException(status_code=422, detail="Invalid unit name")
    exists = db.query(MeasurementUnit).filter(MeasurementUnit.tenant_id == current_user.tenant_id, ((MeasurementUnit.key == key) | (func.lower(MeasurementUnit.name) == payload.name.lower()))).first()
    if exists: raise HTTPException(status_code=409, detail="Unit already exists")
    item = MeasurementUnit(tenant_id=current_user.tenant_id, key=key, is_active=True, **payload.model_dump())
    db.add(item); db.commit(); db.refresh(item); return _unit(item)


@router.patch("/units/{unit_id}", response_model=UnitResponse)
def update_unit(unit_id: uuid.UUID, payload: UpdateUnitRequest, db: Session = Depends(get_db), current_user: User = Depends(require_permission("products.update"))):
    item = db.query(MeasurementUnit).filter(MeasurementUnit.id == unit_id, MeasurementUnit.tenant_id == current_user.tenant_id).first()
    if not item: raise HTTPException(status_code=404, detail="Unit not found")
    duplicate = db.query(MeasurementUnit).filter(MeasurementUnit.tenant_id == current_user.tenant_id, func.lower(MeasurementUnit.name) == payload.name.lower(), MeasurementUnit.id != item.id).first()
    if duplicate: raise HTTPException(status_code=409, detail="Unit already exists")
    if not payload.is_active and db.query(Product).filter(Product.tenant_id == current_user.tenant_id, Product.unit_id == item.id, Product.status == "active").first():
        raise HTTPException(status_code=409, detail="Unit has active products")
    # No se cambia el tipo si la usan productos/servicios del tipo anterior.
    if payload.item_type != item.item_type and db.query(Product).filter(Product.tenant_id == current_user.tenant_id, Product.unit_id == item.id, Product.item_type != payload.item_type).first():
        raise HTTPException(status_code=409, detail="Unit is used by items of another type")
    item.name, item.abbreviation, item.item_type, item.is_active = payload.name, payload.abbreviation, payload.item_type, payload.is_active
    db.commit(); db.refresh(item); return _unit(item)


@router.get("/brands", response_model=list[BrandResponse])
def list_brands(search: str = Query(default="", max_length=100), include_inactive: bool = False, db: Session = Depends(get_db), current_user: User = Depends(require_permission("products.view"))):
    query = db.query(Brand).filter(Brand.tenant_id == current_user.tenant_id)
    if not include_inactive: query = query.filter(Brand.is_active.is_(True))
    if search.strip(): query = query.filter(Brand.name.ilike(f"%{search.strip()}%"))
    return [_brand(item) for item in query.order_by(Brand.name).all()]


@router.post("/brands", response_model=BrandResponse, status_code=status.HTTP_201_CREATED)
def create_brand(payload: CreateBrandRequest, db: Session = Depends(get_db), current_user: User = Depends(require_permission("products.update"))):
    exists = db.query(Brand).filter(Brand.tenant_id == current_user.tenant_id, func.lower(Brand.name) == payload.name.lower()).first()
    if exists: raise HTTPException(status_code=409, detail="Brand already exists")
    item = Brand(tenant_id=current_user.tenant_id, is_active=True, **payload.model_dump())
    db.add(item); db.commit(); db.refresh(item); return _brand(item)


@router.patch("/brands/{brand_id}", response_model=BrandResponse)
def update_brand(brand_id: uuid.UUID, payload: UpdateBrandRequest, db: Session = Depends(get_db), current_user: User = Depends(require_permission("products.update"))):
    item = db.query(Brand).filter(Brand.id == brand_id, Brand.tenant_id == current_user.tenant_id).first()
    if not item: raise HTTPException(status_code=404, detail="Brand not found")
    duplicate = db.query(Brand).filter(Brand.tenant_id == current_user.tenant_id, func.lower(Brand.name) == payload.name.lower(), Brand.id != item.id).first()
    if duplicate: raise HTTPException(status_code=409, detail="Brand already exists")
    if not payload.is_active and db.query(Product).filter(Product.tenant_id == current_user.tenant_id, Product.brand_id == item.id, Product.status == "active").first():
        raise HTTPException(status_code=409, detail="Brand has active products")
    item.name, item.description, item.is_active = payload.name, payload.description, payload.is_active
    db.commit(); db.refresh(item); return _brand(item)


# --- Categorías ----------------------------------------------------------------
def _category(db: Session, item: ProductCategory) -> CategoryResponse:
    count = db.query(func.count(Product.id)).filter(Product.category_id == item.id).scalar() or 0
    return CategoryResponse(id=str(item.id), name=item.name, description=item.description, is_active=item.is_active, product_count=count, created_at=item.created_at)


@router.get("/categories", response_model=list[CategoryResponse])
def list_categories(search: str = Query(default="", max_length=80), include_inactive: bool = False, db: Session = Depends(get_db), current_user: User = Depends(require_permission("products.view"))):
    query = db.query(ProductCategory).filter(ProductCategory.tenant_id == current_user.tenant_id)
    if not include_inactive: query = query.filter(ProductCategory.is_active.is_(True))
    if search.strip(): query = query.filter(ProductCategory.name.ilike(f"%{search.strip()}%"))
    return [_category(db, item) for item in query.order_by(ProductCategory.name).all()]


@router.post("/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(payload: CreateCategoryRequest, db: Session = Depends(get_db), current_user: User = Depends(require_permission("products.update"))):
    exists = db.query(ProductCategory).filter(ProductCategory.tenant_id == current_user.tenant_id, func.lower(ProductCategory.name) == payload.name.lower()).first()
    if exists: raise HTTPException(status_code=409, detail="Category already exists")
    item = ProductCategory(tenant_id=current_user.tenant_id, is_active=True, **payload.model_dump())
    db.add(item); db.commit(); db.refresh(item); return _category(db, item)


@router.patch("/categories/{category_id}", response_model=CategoryResponse)
def update_category(category_id: uuid.UUID, payload: UpdateCategoryRequest, db: Session = Depends(get_db), current_user: User = Depends(require_permission("products.update"))):
    item = db.query(ProductCategory).filter(ProductCategory.id == category_id, ProductCategory.tenant_id == current_user.tenant_id).first()
    if not item: raise HTTPException(status_code=404, detail="Category not found")
    duplicate = db.query(ProductCategory).filter(ProductCategory.tenant_id == current_user.tenant_id, func.lower(ProductCategory.name) == payload.name.lower(), ProductCategory.id != item.id).first()
    if duplicate: raise HTTPException(status_code=409, detail="Category already exists")
    if not payload.is_active and db.query(Product).filter(Product.tenant_id == current_user.tenant_id, Product.category_id == item.id, Product.status == "active").first():
        raise HTTPException(status_code=409, detail="Category has active products")
    item.name, item.description, item.is_active = payload.name, payload.description, payload.is_active
    db.commit(); db.refresh(item); return _category(db, item)
