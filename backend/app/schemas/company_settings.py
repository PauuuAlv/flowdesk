from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field, field_validator


class CompanySettingsPayload(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    legal_name: str | None = Field(default=None, max_length=255)
    tax_id: str | None = Field(default=None, max_length=20, pattern=r"^[A-Za-z0-9&Ññ-]*$")
    contact_email: EmailStr | None = None
    contact_phone: str | None = Field(default=None, max_length=30)
    website: str | None = Field(default=None, max_length=255)
    logo_url: str | None = Field(default=None, max_length=500)
    address_line: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    postal_code: str | None = Field(default=None, max_length=12)
    country: str = Field(min_length=2, max_length=80)
    currency: str = Field(min_length=3, max_length=3, pattern=r"^[A-Za-z]{3}$")
    default_tax_rate: Decimal = Field(ge=0, le=100, max_digits=5, decimal_places=2)
    quote_validity_days: int = Field(ge=1, le=365)
    quote_prefix: str = Field(min_length=1, max_length=12, pattern=r"^[A-Za-z0-9-]+$")
    payment_instructions: str | None = Field(default=None, max_length=1500)

    @field_validator("name", "legal_name", "contact_phone", "address_line", "city", "state", "country")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        normalized = " ".join(value.split()) if value else None
        return normalized or None

    @field_validator("tax_id", "currency", "quote_prefix", mode="before")
    @classmethod
    def normalize_code(cls, value: str | None) -> str | None:
        return value.strip().upper() if value else None

    @field_validator("website", "logo_url", "postal_code", "payment_instructions")
    @classmethod
    def normalize_optional(cls, value: str | None) -> str | None:
        normalized = value.strip() if value else None
        return normalized or None


class CompanySettingsResponse(CompanySettingsPayload):
    id: str
    slug: str
