from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class CreateUnitRequest(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    abbreviation: str = Field(min_length=1, max_length=15)

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
