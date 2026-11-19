import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

PlanKey = Literal["basic", "professional", "enterprise"]
SubscriptionStatus = Literal["trial", "active", "suspended", "cancelled"]


class PlatformAdminLoginRequest(BaseModel):
    email: EmailStr
    password: str


class PlatformAdminTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    # NOTA: a diferencia de User, por ahora PlatformAdmin no tiene refresh token
    # (son pocos usuarios, de ArmSystem, con sesiones más cortas está bien).
    # Si en el futuro hace falta, se agrega igual que en security/jwt.py para User.


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
    # SOLO PARA DESARROLLO: mientras no haya envío de correo real (SES/boto3),
    # regresamos el link de invitación en la respuesta para poder probar el
    # flujo manualmente. ANTES DE PRODUCCIÓN esto debe quitarse y mandarse
    # únicamente por correo — nunca en la respuesta del API.
    dev_invitation_link: str


class TenantUsageResponse(BaseModel):
    users: int
    clients: int
    products: int


# --- Gestión de empresas (tenants) desde la administración de plataforma ---

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class TenantSummary(BaseModel):
    id: str
    name: str
    slug: str
    is_active: bool
    created_at: datetime | None
    admin_email: str | None
    admin_full_name: str | None
    users_count: int
    active_users_count: int
    # Plan y suscripción SaaS
    plan_key: PlanKey
    plan_name: str
    subscription_status: SubscriptionStatus
    max_users: int
    max_clients: int
    max_products: int
    usage: TenantUsageResponse
    subscription_started_at: datetime | None
    subscription_renews_at: datetime | None


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


# Compatibilidad: la vista de suscripciones usa la misma respuesta unificada.
TenantSaaSResponse = TenantSummary
