from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

PlanKey = Literal["basic", "professional", "enterprise"]
SubscriptionStatus = Literal["trial", "active", "suspended", "cancelled"]


class PlatformAdminLoginRequest(BaseModel):
    email: EmailStr
    password: str


class PlatformAdminTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


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
    clients: int
    products: int


class TenantSaaSResponse(BaseModel):
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
    subscription_started_at: datetime
    subscription_renews_at: datetime | None
    created_at: datetime


class UpdateTenantSubscriptionRequest(BaseModel):
    plan_key: PlanKey
    subscription_status: SubscriptionStatus
    subscription_renews_at: datetime | None = None
