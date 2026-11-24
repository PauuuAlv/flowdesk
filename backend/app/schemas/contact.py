from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


class ContactPayload(BaseModel):
    """Datos de un contacto. client_id viene de la URL y tenant_id del JWT."""

    full_name: str = Field(min_length=2, max_length=120)
    job_title: str | None = Field(default=None, max_length=120)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=30, pattern=r"^[0-9+()\-\s.]*$")
    is_primary: bool = False

    @field_validator("full_name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value):
        if value is None:
            return None
        normalized = str(value).strip().lower()
        return normalized or None

    @field_validator("job_title", "phone", mode="before")
    @classmethod
    def normalize_optional_text(cls, value):
        if value is None:
            return None
        normalized = " ".join(str(value).split())
        return normalized or None


class CreateContactRequest(ContactPayload):
    pass


class UpdateContactRequest(ContactPayload):
    pass


class ContactResponse(BaseModel):
    id: str
    client_id: str
    full_name: str
    job_title: str | None
    email: str | None
    phone: str | None
    is_primary: bool
    created_at: datetime
    updated_at: datetime
