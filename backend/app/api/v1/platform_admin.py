from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.models.client import Client
from app.models.product import Product
from app.models.tenant import Tenant
from app.core.plans import get_plan
from app.repositories.platform_admin_repository import PlatformAdminRepository
from app.repositories.tenant_repository import TenantRepository
from app.schemas.platform_admin import (
    PlatformAdminLoginRequest,
    PlatformAdminTokenResponse,
    CreateTenantRequest,
    CreateTenantResponse,
    TenantSaaSResponse,
    TenantUsageResponse,
    UpdateTenantSubscriptionRequest,
)
from app.security.jwt import create_platform_admin_token
from app.security.password import verify_password
from app.security.platform_admin_auth import get_current_platform_admin
from app.security.tokens import generate_raw_token, hash_token
from app.services.access_control import create_role_templates
from app.services.email import EmailService, get_email_service

router = APIRouter()


def _serialize_tenant(db: Session, tenant: Tenant) -> TenantSaaSResponse:
    plan = get_plan(tenant.plan_key)
    return TenantSaaSResponse(
        id=str(tenant.id), name=tenant.name, slug=tenant.slug,
        plan_key=tenant.plan_key, plan_name=plan["name"],
        subscription_status=tenant.subscription_status, is_active=tenant.is_active,
        max_users=tenant.max_users, max_clients=tenant.max_clients,
        max_products=tenant.max_products,
        usage=TenantUsageResponse(
            users=db.query(func.count(User.id)).filter(User.tenant_id == tenant.id).scalar() or 0,
            clients=db.query(func.count(Client.id)).filter(Client.tenant_id == tenant.id).scalar() or 0,
            products=db.query(func.count(Product.id)).filter(Product.tenant_id == tenant.id).scalar() or 0,
        ),
        subscription_started_at=tenant.subscription_started_at,
        subscription_renews_at=tenant.subscription_renews_at,
        created_at=tenant.created_at,
    )


@router.post("/auth/login", response_model=PlatformAdminTokenResponse)
def platform_admin_login(payload: PlatformAdminLoginRequest, db: Session = Depends(get_db)):
    admin_repo = PlatformAdminRepository()
    admin = admin_repo.find_by_email(db, payload.email)

    invalid_credentials = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid email or password",
    )
    if not admin or not verify_password(payload.password, admin.hashed_password):
        raise invalid_credentials

    token = create_platform_admin_token(admin_id=admin.id)
    return PlatformAdminTokenResponse(access_token=token)


@router.post(
    "/tenants",
    response_model=CreateTenantResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_tenant(
    payload: CreateTenantRequest,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_platform_admin),  # protegido: solo PlatformAdmin
    email_service: EmailService = Depends(get_email_service),
):
    tenant_repo = TenantRepository()

    if tenant_repo.find_by_slug(db, payload.slug):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slug already in use")

    plan = get_plan(payload.plan_key)
    tenant = tenant_repo.create(
        db, name=payload.name, slug=payload.slug, plan_key=payload.plan_key,
        subscription_status="trial", max_users=plan["max_users"],
        max_clients=plan["max_clients"], max_products=plan["max_products"],
        subscription_renews_at=datetime.now(timezone.utc) + timedelta(days=30),
    )
    template_roles = create_role_templates(db, tenant.id)

    # Crea el primer usuario del tenant como admin, invitado (sin password todavía).
    raw_token = generate_raw_token()
    admin_user = User(
        tenant_id=tenant.id,
        email=payload.admin_email,
        full_name=payload.admin_full_name,
        role="admin",
        role_id=template_roles["admin"].id,
        status="invited",
        hashed_password=None,
        invited_by_user_id=None,  # lo invitó un PlatformAdmin, no otro User
        invitation_token_hash=hash_token(raw_token),
        invitation_expires_at=datetime.now(timezone.utc)
        + timedelta(days=settings.INVITATION_TOKEN_EXPIRE_DAYS),
    )
    db.add(admin_user)
    db.commit()
    db.refresh(tenant)
    db.refresh(admin_user)

    invitation_link = f"{settings.FRONTEND_URL}/accept-invite?token={raw_token}"
    email_service.send_invitation(
        recipient=admin_user.email,
        recipient_name=admin_user.full_name,
        invitation_url=invitation_link,
        tenant_name=tenant.name,
    )

    return CreateTenantResponse(
        tenant_id=str(tenant.id),
        tenant_name=tenant.name,
        tenant_slug=tenant.slug,
        admin_user_id=str(admin_user.id),
        admin_email=admin_user.email,
        invitation_link=invitation_link,
    )


@router.get("/tenants", response_model=list[TenantSaaSResponse])
def list_tenants(
    db: Session = Depends(get_db),
    _admin=Depends(get_current_platform_admin),
):
    tenants = db.query(Tenant).order_by(Tenant.created_at.desc()).all()
    return [_serialize_tenant(db, tenant) for tenant in tenants]


@router.patch("/tenants/{tenant_id}/subscription", response_model=TenantSaaSResponse)
def update_tenant_subscription(
    tenant_id: str,
    payload: UpdateTenantSubscriptionRequest,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_platform_admin),
):
    try:
        import uuid
        parsed_id = uuid.UUID(tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid tenant identifier") from exc
    tenant = db.query(Tenant).filter(Tenant.id == parsed_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    plan = get_plan(payload.plan_key)
    tenant.plan_key = payload.plan_key
    tenant.subscription_status = payload.subscription_status
    tenant.is_active = payload.subscription_status in ("trial", "active")
    tenant.max_users = plan["max_users"]
    tenant.max_clients = plan["max_clients"]
    tenant.max_products = plan["max_products"]
    tenant.subscription_renews_at = payload.subscription_renews_at
    db.commit()
    db.refresh(tenant)
    return _serialize_tenant(db, tenant)
