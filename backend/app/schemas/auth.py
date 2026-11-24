from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.validators import validate_password_strength


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class RegisterRequest(BaseModel):
    """Datos requeridos para activar una cuenta mediante invitación."""

    token: str
    password: str

    @field_validator("password")
    @classmethod
    def strong_password(cls, value: str) -> str:
        return validate_password_strength(value)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def strong_password(cls, value: str) -> str:
        return validate_password_strength(value)


class MessageResponse(BaseModel):
    message: str


class UpdateProfileRequest(BaseModel):
    """Datos que cada usuario puede cambiar de su propia cuenta."""

    full_name: str = Field(min_length=2, max_length=120)

    @field_validator("full_name")
    @classmethod
    def normalize_full_name(cls, value: str) -> str:
        value = " ".join(value.split())
        if len(value) < 2:
            raise ValueError("Full name must be at least 2 characters long")
        return value


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str

    @field_validator("new_password")
    @classmethod
    def strong_password(cls, value: str) -> str:
        return validate_password_strength(value)
