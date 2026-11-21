from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.platform_admin import PlanKey, SubscriptionStatus


class TenantPlanUsage(BaseModel):
    users: int
    clients: int
    products: int


class TenantPlanOption(BaseModel):
    key: PlanKey
    name: str
    max_users: int
    max_clients: int
    max_products: int
    features: list[str]


class PlanChangeRequestResponse(BaseModel):
    id: str
    tenant_id: str
    tenant_name: str
    requested_by_name: str
    requested_by_email: str
    current_plan_key: PlanKey
    requested_plan_key: PlanKey
    status: Literal["pending", "approved", "rejected"]
    note: str | None
    created_at: datetime


class TenantPlanResponse(BaseModel):
    plan_key: PlanKey
    plan_name: str
    subscription_status: SubscriptionStatus
    subscription_started_at: datetime
    subscription_renews_at: datetime | None
    billing_email: str | None
    max_users: int
    max_clients: int
    max_products: int
    usage: TenantPlanUsage
    plans: list[TenantPlanOption]
    current_request: PlanChangeRequestResponse | None


class CreatePlanChangeRequest(BaseModel):
    requested_plan_key: PlanKey
    note: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def clean_note(self):
        self.note = self.note.strip() if self.note else None
        return self


class ResolvePlanChangeRequest(BaseModel):
    status: Literal["approved", "rejected"]
