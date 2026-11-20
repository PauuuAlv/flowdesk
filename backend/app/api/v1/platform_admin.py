from datetime import datetime, timedelta, timezone
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.models.client import Client
from app.models.activity import Activity
from app.models.opportunity import Opportunity
from app.models.product import Product
from app.models.quote import Quote
from app.models.platform_audit import PlatformAuditLog
from app.models.platform_admin import PlatformAdmin
from app.models.plan_change_request import PlanChangeRequest
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
    SaaSPlanResponse,
    PlatformAuditResponse,
    PlatformAdminMeResponse,
    InvitePlatformMemberRequest,
    PlatformMemberResponse,
    AcceptPlatformInvitationRequest,
)
from app.schemas.tenant_plan import PlanChangeRequestResponse, ResolvePlanChangeRequest
from app.security.jwt import create_platform_admin_token
from app.security.password import hash_password, verify_password
from app.security.platform_admin_auth import get_current_platform_admin, require_platform_superadmin
from app.security.tokens import generate_raw_token, hash_token
from app.services.access_control import create_opportunity_stage_templates, create_product_catalog_templates, create_role_templates
from app.services.email import EmailService, get_email_service

router = APIRouter()


def _serialize_tenant(db: Session, tenant: Tenant) -> TenantSaaSResponse:
    plan = get_plan(tenant.plan_key)
    primary_admin = (
        db.query(User)
        .filter(User.tenant_id == tenant.id, User.role == "admin")
        .order_by(User.created_at.asc())
        .first()
    )
    return TenantSaaSResponse(
        id=str(tenant.id), name=tenant.name, slug=tenant.slug,
        plan_key=tenant.plan_key, plan_name=plan["name"],
        subscription_status=tenant.subscription_status, is_active=tenant.is_active,
        max_users=tenant.max_users, max_clients=tenant.max_clients,
        max_products=tenant.max_products,
        usage=TenantUsageResponse(
            users=db.query(func.count(User.id)).filter(User.tenant_id == tenant.id).scalar() or 0,
            active_users=db.query(func.count(User.id)).filter(
                User.tenant_id == tenant.id, User.status == "active"
            ).scalar() or 0,
            invited_users=db.query(func.count(User.id)).filter(
                User.tenant_id == tenant.id, User.status == "invited"
            ).scalar() or 0,
            clients=db.query(func.count(Client.id)).filter(Client.tenant_id == tenant.id).scalar() or 0,
            opportunities=db.query(func.count(Opportunity.id)).filter(
                Opportunity.tenant_id == tenant.id
            ).scalar() or 0,
            activities=db.query(func.count(Activity.id)).filter(
                Activity.tenant_id == tenant.id
            ).scalar() or 0,
            quotes=db.query(func.count(Quote.id)).filter(Quote.tenant_id == tenant.id).scalar() or 0,
            products=db.query(func.count(Product.id)).filter(Product.tenant_id == tenant.id).scalar() or 0,
        ),
        admin_name=primary_admin.full_name if primary_admin else None,
        admin_email=primary_admin.email if primary_admin else None,
        billing_email=tenant.billing_email,
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
    if not admin or not admin.hashed_password or not verify_password(payload.password, admin.hashed_password):
        raise invalid_credentials

    token = create_platform_admin_token(admin_id=admin.id)
    return PlatformAdminTokenResponse(access_token=token)


@router.get("/auth/me", response_model=PlatformAdminMeResponse)
def platform_admin_me(admin=Depends(get_current_platform_admin)):
    return PlatformAdminMeResponse(
        id=str(admin.id), email=admin.email, full_name=admin.full_name, role=admin.role
    )


@router.post("/auth/accept-invite", response_model=PlatformAdminTokenResponse)
def accept_platform_invitation(payload: AcceptPlatformInvitationRequest, db: Session = Depends(get_db)):
    admin = db.query(PlatformAdmin).filter(
        PlatformAdmin.invitation_token_hash == hash_token(payload.token)
    ).first()
    if not admin or not admin.invitation_expires_at or admin.invitation_expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Invalid or expired invitation")
    admin.hashed_password = hash_password(payload.password)
    admin.invitation_token_hash = None
    admin.invitation_expires_at = None
    admin.is_active = True
    db.commit(); db.refresh(admin)
    return PlatformAdminTokenResponse(access_token=create_platform_admin_token(admin.id))


@router.get("/team", response_model=list[PlatformMemberResponse])
def list_platform_team(
    db: Session = Depends(get_db),
    _admin=Depends(require_platform_superadmin),
):
    return [PlatformMemberResponse(
        id=str(item.id), email=item.email, full_name=item.full_name, role=item.role,
        is_active=item.is_active, invitation_pending=item.hashed_password is None,
        created_at=item.created_at,
    ) for item in db.query(PlatformAdmin).order_by(PlatformAdmin.created_at.asc()).all()]


@router.post("/team/invite", response_model=PlatformMemberResponse, status_code=status.HTTP_201_CREATED)
def invite_platform_member(
    payload: InvitePlatformMemberRequest,
    db: Session = Depends(get_db),
    admin=Depends(require_platform_superadmin),
    email_service: EmailService = Depends(get_email_service),
):
    if db.query(PlatformAdmin).filter(func.lower(PlatformAdmin.email) == payload.email.lower()).first():
        raise HTTPException(status_code=409, detail="Platform account already exists")
    raw_token = generate_raw_token()
    member = PlatformAdmin(
        email=payload.email.lower(), full_name=payload.full_name.strip(), role=payload.role,
        hashed_password=None, is_active=True, invitation_token_hash=hash_token(raw_token),
        invitation_expires_at=datetime.now(timezone.utc) + timedelta(days=settings.INVITATION_TOKEN_EXPIRE_DAYS),
    )
    db.add(member); db.flush()
    db.add(PlatformAuditLog(
        platform_admin_id=admin.id, action="platform_member.invited",
        description=f"Se invitó a {member.email} como cuenta de consulta.",
        details={"member_id": str(member.id), "role": member.role},
    ))
    db.commit(); db.refresh(member)
    invitation_link = f"{settings.FRONTEND_URL}/administracion-flowdesk/aceptar-invitacion?token={raw_token}"
    email_service.send_invitation(
        recipient=member.email, recipient_name=member.full_name,
        invitation_url=invitation_link, tenant_name="Equipo de administración de Flowdesk",
    )
    return PlatformMemberResponse(
        id=str(member.id), email=member.email, full_name=member.full_name, role=member.role,
        is_active=member.is_active, invitation_pending=True, created_at=member.created_at,
        invitation_link=invitation_link,
    )


@router.post(
    "/tenants",
    response_model=CreateTenantResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_tenant(
    payload: CreateTenantRequest,
    db: Session = Depends(get_db),
    admin=Depends(require_platform_superadmin),  # protegido: solo superadministrador
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
        billing_email=payload.admin_email,
        subscription_renews_at=datetime.now(timezone.utc) + timedelta(days=30),
    )
    template_roles = create_role_templates(db, tenant.id)
    create_opportunity_stage_templates(db, tenant.id)
    create_product_catalog_templates(db, tenant.id)

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
    db.add(PlatformAuditLog(
        platform_admin_id=admin.id,
        tenant_id=tenant.id,
        action="tenant.created",
        description=f"Se creó la empresa {tenant.name} con el plan {plan['name']}.",
        details={"plan_key": tenant.plan_key, "billing_email": payload.admin_email},
    ))
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


@router.get("/plans", response_model=list[SaaSPlanResponse])
def list_plans(
    db: Session = Depends(get_db),
    _admin=Depends(get_current_platform_admin),
):
    from app.core.plans import PLAN_TEMPLATES

    counts = dict(db.query(Tenant.plan_key, func.count(Tenant.id)).group_by(Tenant.plan_key).all())
    return [
        SaaSPlanResponse(
            key=key,
            name=value["name"],
            max_users=value["max_users"],
            max_clients=value["max_clients"],
            max_products=value["max_products"],
            tenant_count=counts.get(key, 0),
            features=value["features"],
        )
        for key, value in PLAN_TEMPLATES.items()
    ]


@router.get("/audit", response_model=list[PlatformAuditResponse])
def list_platform_audit(
    db: Session = Depends(get_db),
    _admin=Depends(get_current_platform_admin),
):
    items = db.query(PlatformAuditLog).order_by(PlatformAuditLog.created_at.desc()).limit(250).all()
    tenants = {item.id: item.name for item in db.query(Tenant).all()}
    admins = {item.id: item.email for item in db.query(PlatformAdmin).all()}
    return [
        PlatformAuditResponse(
            id=str(item.id),
            action=item.action,
            description=item.description,
            tenant_id=str(item.tenant_id) if item.tenant_id else None,
            tenant_name=tenants.get(item.tenant_id),
            admin_email=admins.get(item.platform_admin_id),
            details=item.details or {},
            created_at=item.created_at,
        )
        for item in items
    ]


@router.get("/subscription-requests", response_model=list[PlanChangeRequestResponse])
def list_subscription_requests(
    db: Session = Depends(get_db),
    _admin=Depends(get_current_platform_admin),
):
    items = db.query(PlanChangeRequest).order_by(PlanChangeRequest.created_at.desc()).all()
    result = []
    for item in items:
        tenant = db.query(Tenant).filter(Tenant.id == item.tenant_id).first()
        user = db.query(User).filter(User.id == item.requested_by_user_id).first()
        if tenant and user:
            result.append(PlanChangeRequestResponse(
                id=str(item.id), tenant_id=str(tenant.id), tenant_name=tenant.name,
                requested_by_name=user.full_name or user.email, requested_by_email=user.email,
                current_plan_key=item.current_plan_key,
                requested_plan_key=item.requested_plan_key, status=item.status,
                note=item.note, created_at=item.created_at,
            ))
    return result


@router.patch("/subscription-requests/{request_id}", response_model=PlanChangeRequestResponse)
def resolve_subscription_request(
    request_id: uuid.UUID,
    payload: ResolvePlanChangeRequest,
    db: Session = Depends(get_db),
    admin=Depends(require_platform_superadmin),
):
    item = db.query(PlanChangeRequest).filter(PlanChangeRequest.id == request_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Plan change request not found")
    if item.status != "pending":
        raise HTTPException(status_code=409, detail="Plan change request already resolved")
    tenant = db.query(Tenant).filter(Tenant.id == item.tenant_id).first()
    user = db.query(User).filter(User.id == item.requested_by_user_id).first()
    if not tenant or not user:
        raise HTTPException(status_code=404, detail="Related tenant or user not found")
    if payload.status == "approved":
        plan = get_plan(item.requested_plan_key)
        tenant.plan_key = item.requested_plan_key
        tenant.max_users = plan["max_users"]
        tenant.max_clients = plan["max_clients"]
        tenant.max_products = plan["max_products"]
    item.status = payload.status
    item.resolved_by_admin_id = admin.id
    db.add(PlatformAuditLog(
        platform_admin_id=admin.id, tenant_id=tenant.id,
        action=f"plan_change.{payload.status}",
        description=f"La solicitud de cambio de plan de {tenant.name} fue {'aprobada' if payload.status == 'approved' else 'rechazada'}.",
        details={"before": item.current_plan_key, "requested": item.requested_plan_key},
    ))
    db.commit(); db.refresh(item)
    return PlanChangeRequestResponse(
        id=str(item.id), tenant_id=str(tenant.id), tenant_name=tenant.name,
        requested_by_name=user.full_name or user.email, requested_by_email=user.email,
        current_plan_key=item.current_plan_key, requested_plan_key=item.requested_plan_key,
        status=item.status, note=item.note, created_at=item.created_at,
    )


@router.patch("/tenants/{tenant_id}/subscription", response_model=TenantSaaSResponse)
def update_tenant_subscription(
    tenant_id: str,
    payload: UpdateTenantSubscriptionRequest,
    db: Session = Depends(get_db),
    admin=Depends(require_platform_superadmin),
):
    try:
        import uuid
        parsed_id = uuid.UUID(tenant_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Invalid tenant identifier") from exc
    tenant = db.query(Tenant).filter(Tenant.id == parsed_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    old_plan_key = tenant.plan_key
    old_status = tenant.subscription_status
    old_billing_email = tenant.billing_email
    plan = get_plan(payload.plan_key)
    tenant.plan_key = payload.plan_key
    tenant.subscription_status = payload.subscription_status
    tenant.is_active = payload.subscription_status in ("trial", "active")
    tenant.max_users = plan["max_users"]
    tenant.max_clients = plan["max_clients"]
    tenant.max_products = plan["max_products"]
    tenant.subscription_renews_at = payload.subscription_renews_at
    if payload.billing_email is not None:
        tenant.billing_email = str(payload.billing_email)
    changes = {}
    if old_plan_key != tenant.plan_key:
        changes["plan"] = {"before": old_plan_key, "after": tenant.plan_key}
    if old_status != tenant.subscription_status:
        changes["status"] = {"before": old_status, "after": tenant.subscription_status}
    if old_billing_email != tenant.billing_email:
        changes["billing_email"] = {"before": old_billing_email, "after": tenant.billing_email}
    if changes:
        db.add(PlatformAuditLog(
            platform_admin_id=admin.id,
            tenant_id=tenant.id,
            action="subscription.updated",
            description=f"Se actualizó la suscripción de {tenant.name}.",
            details=changes,
        ))
    db.commit()
    db.refresh(tenant)
    return _serialize_tenant(db, tenant)
