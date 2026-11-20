from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.plans import PLAN_TEMPLATES, get_plan
from app.models.client import Client
from app.models.plan_change_request import PlanChangeRequest
from app.models.platform_audit import PlatformAuditLog
from app.models.product import Product
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.tenant_plan import (
    CreatePlanChangeRequest,
    PlanChangeRequestResponse,
    TenantPlanOption,
    TenantPlanResponse,
    TenantPlanUsage,
)
from app.security.permissions import require_permission

router = APIRouter()


def _request_response(item: PlanChangeRequest, tenant: Tenant, user: User) -> PlanChangeRequestResponse:
    return PlanChangeRequestResponse(
        id=str(item.id), tenant_id=str(tenant.id), tenant_name=tenant.name,
        requested_by_name=user.full_name or user.email, requested_by_email=user.email,
        current_plan_key=item.current_plan_key, requested_plan_key=item.requested_plan_key,
        status=item.status, note=item.note, created_at=item.created_at,
    )


@router.get("", response_model=TenantPlanResponse)
def get_tenant_plan(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("settings.view")),
):
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    pending = db.query(PlanChangeRequest).filter(
        PlanChangeRequest.tenant_id == tenant.id, PlanChangeRequest.status == "pending"
    ).order_by(PlanChangeRequest.created_at.desc()).first()
    plan = get_plan(tenant.plan_key)
    return TenantPlanResponse(
        plan_key=tenant.plan_key, plan_name=plan["name"],
        subscription_status=tenant.subscription_status,
        subscription_started_at=tenant.subscription_started_at,
        subscription_renews_at=tenant.subscription_renews_at,
        billing_email=tenant.billing_email,
        max_users=tenant.max_users, max_clients=tenant.max_clients,
        max_products=tenant.max_products,
        usage=TenantPlanUsage(
            users=db.query(func.count(User.id)).filter(User.tenant_id == tenant.id).scalar() or 0,
            clients=db.query(func.count(Client.id)).filter(Client.tenant_id == tenant.id).scalar() or 0,
            products=db.query(func.count(Product.id)).filter(Product.tenant_id == tenant.id).scalar() or 0,
        ),
        plans=[TenantPlanOption(key=key, **value) for key, value in PLAN_TEMPLATES.items()],
        current_request=_request_response(pending, tenant, current_user) if pending else None,
    )


@router.post("/change-requests", response_model=PlanChangeRequestResponse, status_code=status.HTTP_201_CREATED)
def request_plan_change(
    payload: CreatePlanChangeRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("settings.view")),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only tenant administrators can request plan changes")
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    if payload.requested_plan_key == tenant.plan_key:
        raise HTTPException(status_code=409, detail="Requested plan is already active")
    existing = db.query(PlanChangeRequest).filter(
        PlanChangeRequest.tenant_id == tenant.id, PlanChangeRequest.status == "pending"
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="A pending request already exists")
    item = PlanChangeRequest(
        tenant_id=tenant.id, requested_by_user_id=current_user.id,
        current_plan_key=tenant.plan_key, requested_plan_key=payload.requested_plan_key,
        status="pending", note=payload.note,
    )
    db.add(item)
    db.add(PlatformAuditLog(
        tenant_id=tenant.id, action="plan_change.requested",
        description=f"{tenant.name} solicitó cambiar al plan {get_plan(payload.requested_plan_key)['name']}.",
        details={"before": tenant.plan_key, "requested": payload.requested_plan_key},
    ))
    db.commit(); db.refresh(item)
    return _request_response(item, tenant, current_user)
