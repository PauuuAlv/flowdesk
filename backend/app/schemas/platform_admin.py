import re
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.validators import validate_password_strength

PlanKey = Literal["basic", "professional", "enterprise"]
SubscriptionStatus = Literal["trial", "active", "suspended", "cancelled"]
# 'superadmin' | 'operator' | 'viewer' para roles por defecto, 'custom' si no.
PlatformRoleKey = Literal["superadmin", "operator", "viewer", "custom"]


class PlatformAdminLoginRequest(BaseModel):
    email: EmailStr
    password: str


class PlatformAdminTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class PlatformAdminMeResponse(BaseModel):
    id: str
    email: str
    full_name: str | None
    role: PlatformRoleKey
    role_id: str
    role_name: str
    permissions: list[str]
    is_owner: bool


class InvitePlatformMemberRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=3, max_length=255)
    role_id: uuid.UUID


class UpdatePlatformMemberRoleRequest(BaseModel):
    role_id: uuid.UUID


class UpdatePlatformMemberStatusRequest(BaseModel):
    is_active: bool


class PlatformMemberResponse(BaseModel):
    id: str
    email: str
    full_name: str | None
    role: PlatformRoleKey
    role_id: str
    role_name: str
    is_active: bool
    # Cuenta principal (SUPERADMIN_EMAIL del .env): no se le cambia el rol ni se desactiva.
    is_owner: bool
    invitation_pending: bool
    created_at: datetime
    invitation_link: str | None = None


class UpdatePlatformProfileRequest(BaseModel):
    """Datos que cada integrante puede cambiar de su propia cuenta."""
    full_name: str = Field(min_length=2, max_length=120)

    @field_validator("full_name")
    @classmethod
    def normalize_full_name(cls, value: str) -> str:
        value = " ".join(value.split())
        if len(value) < 2:
            raise ValueError("Full name must be at least 2 characters long")
        return value


class ChangePlatformPasswordRequest(BaseModel):
    current_password: str = Field(min_length=1)
    new_password: str

    @field_validator("new_password")
    @classmethod
    def strong_password(cls, value: str) -> str:
        return validate_password_strength(value)


class PlatformForgotPasswordRequest(BaseModel):
    email: EmailStr


class PlatformResetPasswordRequest(BaseModel):
    token: str = Field(min_length=1)
    new_password: str

    @field_validator("new_password")
    @classmethod
    def strong_password(cls, value: str) -> str:
        return validate_password_strength(value)


class AcceptPlatformInvitationRequest(BaseModel):
    token: str
    password: str

    @field_validator("password")
    @classmethod
    def strong_password(cls, value: str) -> str:
        return validate_password_strength(value)


class CreateTenantRequest(BaseModel):
    name: str
    slug: str
    admin_email: EmailStr
    admin_full_name: str | None = None
    plan_key: PlanKey = "basic"


class CreateTenantResponse(BaseModel):
    tenant_id: str
    tenant_name: str
    tenant_slug: str
    admin_user_id: str
    admin_email: str
    invitation_link: str


class TenantUsageResponse(BaseModel):
    users: int
    active_users: int
    invited_users: int
    clients: int
    opportunities: int
    activities: int
    quotes: int
    products: int


# --- Gestión de empresas (tenants) desde la administración de plataforma ---

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class TenantSaaSResponse(BaseModel):
    """Respuesta única de empresa para la administración de plataforma:
    datos generales, administrador principal, plan, suscripción y consumo."""

    id: str
    name: str
    slug: str
    plan_key: PlanKey
    plan_name: str
    subscription_status: SubscriptionStatus
    is_active: bool
    max_users: int
    max_clients: int
    max_products: int
    usage: TenantUsageResponse
    admin_name: str | None
    admin_email: str | None
    billing_email: str | None
    subscription_started_at: datetime
    subscription_renews_at: datetime | None
    created_at: datetime


class UpdateTenantRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    slug: str = Field(min_length=2, max_length=100)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if len(normalized) < 2:
            raise ValueError("Name must have at least 2 characters")
        return normalized

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not SLUG_PATTERN.match(normalized):
            raise ValueError("Slug may only contain lowercase letters, numbers and hyphens")
        return normalized


class UpdateTenantStatusRequest(BaseModel):
    is_active: bool


class UpdateTenantSubscriptionRequest(BaseModel):
    plan_key: PlanKey
    subscription_status: SubscriptionStatus
    subscription_renews_at: datetime | None = None
    billing_email: EmailStr | None = None


class SaaSPlanResponse(BaseModel):
    key: PlanKey
    name: str
    max_users: int
    max_clients: int
    max_products: int
    tenant_count: int
    features: list[str]


