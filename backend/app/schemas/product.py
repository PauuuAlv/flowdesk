from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.core.currencies import CurrencyCode

ProductType = Literal["product", "service"]
ProductStatus = Literal["active", "inactive"]


class ProductPayload(BaseModel):
    name: str = Field(min_length=2, max_length=140)
    sku: str = Field(min_length=2, max_length=50, pattern=r"^[A-Za-z0-9._-]+$")
    description: str | None = Field(default=None, max_length=1000)
    # Categoría del catálogo de la empresa (opcional).
    category_id: str | None = None
    item_type: ProductType
    unit_id: str
    brand_id: str | None = None
    base_price: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    # Moneda del precio. Sin indicarla: al crear, la de la empresa; al editar, la actual.
    currency: CurrencyCode | None = None
    tax_rate: Decimal = Field(ge=0, le=100, max_digits=5, decimal_places=2)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("sku", mode="before")
    @classmethod
    def normalize_sku(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("description")
    @classmethod
    def normalize_optional(cls, value: str | None) -> str | None:
        normalized = " ".join(value.split()) if value else None
        return normalized or None


class CreateProductRequest(ProductPayload):
    sku: str | None = Field(default=None, max_length=50, pattern=r"^[A-Za-z0-9._-]+$")

    @field_validator("sku", mode="before")
    @classmethod
    def normalize_optional_sku(cls, value: str | None) -> str | None:
        return value.strip().upper() if value and value.strip() else None


class UpdateProductRequest(ProductPayload):
    status: ProductStatus


class UpdateProductStatusRequest(BaseModel):
    status: ProductStatus


class ProductResponse(ProductPayload):
    id: str
    category: str | None
    currency: str
    unit: str
    unit_name: str
    unit_abbreviation: str
    brand_name: str | None
    status: ProductStatus
    created_at: datetime
    updated_at: datetime
