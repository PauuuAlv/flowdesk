from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field

PlanKey = Literal["basic", "professional", "enterprise"]
SubscriptionStatus = Literal["trial", "active", "suspended", "cancelled"]
PlatformRole = Literal["superadmin", "viewer"]


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
    role: PlatformRole


class InvitePlatformMemberRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=3, max_length=255)
    role: Literal["viewer"] = "viewer"


class PlatformMemberResponse(BaseModel):
    id: str
    email: str
    full_name: str | None
    role: PlatformRole
    is_active: bool
    invitation_pending: bool
    created_at: datetime
    invitation_link: str | None = None


class AcceptPlatformInvitationRequest(BaseModel):
    token: str
    password: str = Field(min_length=8)


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
    admin_name: str | None
    admin_email: str | None
    billing_email: str | None
    subscription_started_at: datetime
    subscription_renews_at: datetime | None
    created_at: datetime


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


class PlatformAuditResponse(BaseModel):
    id: str
    action: str
    description: str
    tenant_id: str | None
    tenant_name: str | None
    admin_email: str | None
    details: dict
    created_at: datetime
