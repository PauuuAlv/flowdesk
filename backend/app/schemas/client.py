from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator


class ClientPayload(BaseModel):
    company_name: str = Field(min_length=2, max_length=120)
    contact_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=30)
    notes: str | None = Field(default=None, max_length=1000)

    @field_validator("company_name", "contact_name")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()

    @field_validator("phone", "notes")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class CreateClientRequest(ClientPayload):
    pass


class UpdateClientRequest(ClientPayload):
    status: Literal["active", "inactive"]


class UpdateClientStatusRequest(BaseModel):
    status: Literal["active", "inactive"]


class ClientResponse(BaseModel):
    id: str
    company_name: str
    contact_name: str
    email: str
    phone: str | None
    status: Literal["active", "inactive"]
    notes: str | None
    created_at: datetime
    updated_at: datetime
