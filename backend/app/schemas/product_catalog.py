from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

# Mismos valores que Product.item_type.
UnitType = Literal["product", "service"]


class CreateUnitRequest(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    abbreviation: str = Field(min_length=1, max_length=15)
    item_type: UnitType

    @field_validator("name", "abbreviation")
    @classmethod
    def normalize(cls, value: str) -> str:
        return " ".join(value.split())


class UpdateUnitRequest(CreateUnitRequest):
    is_active: bool


class UnitResponse(BaseModel):
    id: str
    key: str
    name: str
    abbreviation: str
    item_type: UnitType
    is_active: bool
    created_at: datetime


class CreateBrandRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=300)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        value = " ".join(value.split()) if value else None
        return value or None


class UpdateBrandRequest(CreateBrandRequest):
    is_active: bool


class BrandResponse(BaseModel):
    id: str
    name: str
    description: str | None
    is_active: bool
    created_at: datetime


class CreateCategoryRequest(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    description: str | None = Field(default=None, max_length=300)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        value = " ".join(value.split()) if value else None
        return value or None


class UpdateCategoryRequest(CreateCategoryRequest):
    is_active: bool


class CategoryResponse(BaseModel):
    id: str
    name: str
    description: str | None
    is_active: bool
    product_count: int
    created_at: datetime
