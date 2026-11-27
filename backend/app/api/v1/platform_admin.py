from datetime import datetime, timedelta, timezone
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
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
from app.models.platform_role import PlatformRole
from app.models.plan_change_request import PlanChangeRequest
from app.models.tenant import Tenant
from app.core.permissions import ADMIN_ROLE_KEY
from app.core.platform_permissions import SUPERADMIN_ROLE_KEY
from app.core.plans import get_plan
from app.models.role import Role
from app.repositories.platform_admin_repository import PlatformAdminRepository
from app.repositories.tenant_repository import TenantRepository
from app.schemas.platform_admin import (
    PlatformAdminLoginRequest,
    PlatformAdminTokenResponse,
    CreateTenantRequest,
    CreateTenantResponse,
    TenantSaaSResponse,
    TenantUsageResponse,
    UpdateTenantRequest,
    UpdateTenantStatusRequest,
    UpdateTenantSubscriptionRequest,
    SaaSPlanResponse,
    PlatformAdminMeResponse,
    InvitePlatformMemberRequest,
    PlatformMemberResponse,
    AcceptPlatformInvitationRequest,
    UpdatePlatformMemberRoleRequest,
    UpdatePlatformMemberStatusRequest,
    UpdatePlatformProfileRequest,
    ChangePlatformPasswordRequest,
    PlatformForgotPasswordRequest,
    PlatformResetPasswordRequest,
)
from app.schemas.audit import AuditFiltersResponse, AuditPageResponse
from app.schemas.auth import MessageResponse
from app.schemas.tenant_plan import PlanChangeRequestResponse, ResolvePlanChangeRequest
from app.security.jwt import create_platform_admin_token
from app.security.password import hash_password, verify_password
from app.security.platform_admin_auth import get_current_platform_admin, require_platform_permission
from app.security.tokens import generate_raw_token, hash_token
from app.services.access_control import (
    create_default_roles,
    create_opportunity_stage_templates,
    create_product_catalog_templates,
)
from app.core.audit import record_event
from app.core.audit_context import get_audit_context
from app.services import audit_queries
from app.services.audit_report import MAX_REPORT_ROWS, build_audit_pdf, resolve_timezone
from app.services.email import EmailService, get_email_service
from app.services.platform_access import count_active_superadmins

router = APIRouter()
logger = logging.getLogger("flowdesk.platform_admin")

# Estados de suscripción con los que la empresa puede operar.
ACTIVE_SUBSCRIPTION_STATUSES = ("trial", "active")


def _serialize_tenant(db: Session, tenant: Tenant) -> TenantSaaSResponse:
    plan = get_plan(tenant.plan_key)
    primary_admin = (
        db.query(User)
        .join(Role, Role.id == User.role_id)
        .filter(User.tenant_id == tenant.id, Role.template_key == ADMIN_ROLE_KEY)
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
    if (
        not admin
        or not admin.is_active
        or not admin.hashed_password
        or not verify_password(payload.password, admin.hashed_password)
    ):
        if admin:
            entry = record_event(
                db, "auth.login_failed", f"Intento de inicio de sesión fallido para {admin.email}",
                scope="platform", entity="platform_admins", entity_id=admin.id,
                details={"reason": "inactive" if not admin.is_active else "wrong_password"},
            )
            entry.actor_type = "anonymous"
            entry.actor_email = payload.email
            db.commit()
        raise invalid_credentials

    get_audit_context().set_platform_admin(admin.id, admin.email)
    record_event(
        db, "auth.login", f"{admin.email} inició sesión en la administración",
        scope="platform", entity="platform_admins", entity_id=admin.id,
    )
    db.commit()
    token = create_platform_admin_token(admin_id=admin.id)
    return PlatformAdminTokenResponse(access_token=token)


@router.get("/auth/me", response_model=PlatformAdminMeResponse)
def platform_admin_me(admin: PlatformAdmin = Depends(get_current_platform_admin)):
    """Identidad y permisos de la cuenta de plataforma que hace la request."""
    return _me_response(admin)


@router.patch("/auth/me", response_model=PlatformAdminMeResponse)
def update_platform_profile(
    payload: UpdatePlatformProfileRequest,
    db: Session = Depends(get_db),
    admin: PlatformAdmin = Depends(get_current_platform_admin),
):
    """Cada integrante puede cambiar su propio nombre (no su correo, rol ni estado)."""
    previous = admin.full_name
    admin.full_name = payload.full_name
    if previous != payload.full_name:
        db.add(PlatformAuditLog(
            platform_admin_id=admin.id, action="platform_profile.updated",
            description=f"{admin.email} actualizó su nombre.",
            details={"before": previous, "after": payload.full_name},
        ))
    db.commit(); db.refresh(admin)
    return _me_response(admin)


@router.post("/auth/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_platform_password(
    payload: ChangePlatformPasswordRequest,
    db: Session = Depends(get_db),
    admin: PlatformAdmin = Depends(get_current_platform_admin),
):
    """Cambio de contraseña con la sesión iniciada: exige la contraseña actual."""
    if not admin.hashed_password or not verify_password(payload.current_password, admin.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    if verify_password(payload.new_password, admin.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New password must be different")
    admin.hashed_password = hash_password(payload.new_password)
    db.add(PlatformAuditLog(
        platform_admin_id=admin.id, action="platform_profile.password_changed",
        description=f"{admin.email} cambió su contraseña.",
        details={},
    ))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/auth/forgot-password", response_model=MessageResponse)
def platform_forgot_password(
    payload: PlatformForgotPasswordRequest,
    db: Session = Depends(get_db),
    email_service: EmailService = Depends(get_email_service),
):
    """SIEMPRE responde el mismo mensaje, exista o no la cuenta, para no
    revelar qué correos pertenecen al equipo de plataforma."""
    generic_response = MessageResponse(
        message="If that email is registered, we've sent password reset instructions."
    )
    admin = PlatformAdminRepository().find_by_email(db, payload.email)
    # Solo cuentas activas que ya definieron contraseña (una invitación pendiente
    # se completa con su propio enlace).
    if not admin or not admin.is_active or not admin.hashed_password:
        return generic_response

    raw_token = generate_raw_token()
    admin.password_reset_token_hash = hash_token(raw_token)
    admin.password_reset_expires_at = datetime.now(timezone.utc) + timedelta(
        hours=settings.RESET_PASSWORD_TOKEN_EXPIRE_HOURS
    )
    db.commit()

    reset_link = f"{settings.FRONTEND_URL}/administracion-flowdesk/restablecer-contrasena?token={raw_token}"
    try:
        email_service.send_password_reset(
            recipient=admin.email, recipient_name=admin.full_name, reset_url=reset_link,
        )
    except Exception:
        logger.exception("Platform password reset email delivery failed")
    return generic_response


@router.post("/auth/reset-password", response_model=MessageResponse)
def platform_reset_password(payload: PlatformResetPasswordRequest, db: Session = Depends(get_db)):
    admin = db.query(PlatformAdmin).filter(
        PlatformAdmin.password_reset_token_hash == hash_token(payload.token)
    ).first()
    if (
        not admin
        or not admin.is_active
        or not admin.password_reset_expires_at
        or admin.password_reset_expires_at < datetime.now(timezone.utc)
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired reset token")

    get_audit_context().set_platform_admin(admin.id, admin.email)
    admin.hashed_password = hash_password(payload.new_password)
    # El enlace es de un solo uso.
    admin.password_reset_token_hash = None
    admin.password_reset_expires_at = None
    db.add(PlatformAuditLog(
        platform_admin_id=admin.id, action="platform_profile.password_reset",
        description=f"{admin.email} restableció su contraseña con un enlace de recuperación.",
        details={},
    ))
    db.commit()
    return MessageResponse(message="Password updated successfully.")


def _me_response(admin: PlatformAdmin) -> PlatformAdminMeResponse:
    return PlatformAdminMeResponse(
        id=str(admin.id),
        email=admin.email,
        full_name=admin.full_name,
        role=admin.role_key,
        role_id=str(admin.role_id),
        role_name=admin.assigned_role.name,
        permissions=admin.permission_codes,
        is_owner=admin.is_owner,
    )


@router.post("/auth/accept-invite", response_model=PlatformAdminTokenResponse)
def accept_platform_invitation(payload: AcceptPlatformInvitationRequest, db: Session = Depends(get_db)):
    admin = db.query(PlatformAdmin).filter(
        PlatformAdmin.invitation_token_hash == hash_token(payload.token)
    ).first()
    if (
        not admin
        or not admin.is_active  # una invitación de una cuenta desactivada ya no sirve
        or not admin.invitation_expires_at
        or admin.invitation_expires_at < datetime.now(timezone.utc)
    ):
        raise HTTPException(status_code=400, detail="Invalid or expired invitation")
    get_audit_context().set_platform_admin(admin.id, admin.email)
    record_event(
        db, "auth.register", f"{admin.email} aceptó su invitación al equipo de plataforma",
        scope="platform", entity="platform_admins", entity_id=admin.id,
    )
    admin.hashed_password = hash_password(payload.password)
    admin.invitation_token_hash = None
    admin.invitation_expires_at = None
    db.commit(); db.refresh(admin)
    return PlatformAdminTokenResponse(access_token=create_platform_admin_token(admin.id))


# --- Equipo de plataforma ---------------------------------------------------

def _serialize_member(member: PlatformAdmin, invitation_link: str | None = None) -> PlatformMemberResponse:
    return PlatformMemberResponse(
        id=str(member.id),
        email=member.email,
        full_name=member.full_name,
        role=member.role_key,
        role_id=str(member.role_id),
        role_name=member.assigned_role.name if member.assigned_role else "Sin rol",
        is_active=member.is_active,
        is_owner=member.is_owner,
        invitation_pending=member.hashed_password is None,
        created_at=member.created_at,
        invitation_link=invitation_link,
    )


def _member_or_404(db: Session, member_id: uuid.UUID) -> PlatformAdmin:
    member = db.query(PlatformAdmin).filter(PlatformAdmin.id == member_id).first()
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Platform member not found")
    return member


def _platform_role_or_404(db: Session, role_id: uuid.UUID) -> PlatformRole:
    role = db.query(PlatformRole).filter(PlatformRole.id == role_id).first()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Platform role not found")
    return role


def _issue_platform_invitation(member: PlatformAdmin) -> str:
    raw_token = generate_raw_token()
    member.invitation_token_hash = hash_token(raw_token)
    member.invitation_expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.INVITATION_TOKEN_EXPIRE_DAYS
    )
    return f"{settings.FRONTEND_URL}/administracion-flowdesk/aceptar-invitacion?token={raw_token}"


def _is_active_superadmin(member: PlatformAdmin) -> bool:
    return (
        member.role_key == SUPERADMIN_ROLE_KEY
        and member.is_active
        and member.hashed_password is not None
    )


@router.get("/team", response_model=list[PlatformMemberResponse])
def list_platform_team(
    db: Session = Depends(get_db),
    _admin=Depends(require_platform_permission("platform.team.view")),
):
    members = db.query(PlatformAdmin).order_by(PlatformAdmin.created_at.asc()).all()
    return [_serialize_member(item) for item in members]


@router.post("/team/invite", response_model=PlatformMemberResponse, status_code=status.HTTP_201_CREATED)
def invite_platform_member(
    payload: InvitePlatformMemberRequest,
    db: Session = Depends(get_db),
    admin: PlatformAdmin = Depends(require_platform_permission("platform.team.invite")),
    email_service: EmailService = Depends(get_email_service),
):
    """Invita a una persona al equipo con cualquier rol de plataforma, incluido
    Superadministrador (puede haber varios)."""
    if db.query(PlatformAdmin).filter(func.lower(PlatformAdmin.email) == payload.email.lower()).first():
        raise HTTPException(status_code=409, detail="Platform account already exists")
    role = _platform_role_or_404(db, payload.role_id)
    member = PlatformAdmin(
        email=payload.email.lower(), full_name=payload.full_name.strip(), role_id=role.id,
        hashed_password=None, is_active=True,
    )
    invitation_link = _issue_platform_invitation(member)
    db.add(member); db.flush()
    db.add(PlatformAuditLog(
        platform_admin_id=admin.id, action="platform_member.invited",
        description=f"Se invitó a {member.email} al equipo de plataforma como {role.name}.",
        details={"member_id": str(member.id), "role_id": str(role.id), "role": role.name},
    ))
    db.commit(); db.refresh(member)
    email_service.send_invitation(
        recipient=member.email, recipient_name=member.full_name,
        invitation_url=invitation_link, tenant_name="Equipo de administración de Flowdesk",
    )
    return _serialize_member(member, invitation_link)


@router.patch("/team/{member_id}/role", response_model=PlatformMemberResponse)
def update_platform_member_role(
    member_id: uuid.UUID,
    payload: UpdatePlatformMemberRoleRequest,
    db: Session = Depends(get_db),
    admin: PlatformAdmin = Depends(require_platform_permission("platform.team.update")),
):
    member = _member_or_404(db, member_id)
    if member.is_owner:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The platform owner account cannot be modified",
        )
    if member.id == admin.id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You cannot change your own role")
    role = _platform_role_or_404(db, payload.role_id)
    if member.role_id == role.id:
        return _serialize_member(member)
    # Nunca dejar a la plataforma sin al menos un Superadministrador activo.
    if (
        _is_active_superadmin(member)
        and role.template_key != SUPERADMIN_ROLE_KEY
        and count_active_superadmins(db, exclude_admin_id=member.id) == 0
    ):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Platform must keep at least one superadmin")
    before = member.assigned_role.name
    member.role_id = role.id
    db.add(PlatformAuditLog(
        platform_admin_id=admin.id, action="platform_member.role_changed",
        description=f"Se cambió el rol de {member.email} de {before} a {role.name}.",
        details={"member_id": str(member.id), "before": before, "after": role.name},
    ))
    db.commit()
    db.refresh(member)
    return _serialize_member(member)


@router.patch("/team/{member_id}/status", response_model=PlatformMemberResponse)
def update_platform_member_status(
    member_id: uuid.UUID,
    payload: UpdatePlatformMemberStatusRequest,
    db: Session = Depends(get_db),
    admin: PlatformAdmin = Depends(require_platform_permission("platform.team.update")),
):
    """Activa o desactiva una cuenta. Una cuenta desactivada no puede iniciar
    sesión y sus tokens ya emitidos dejan de servir."""
    member = _member_or_404(db, member_id)
    if member.is_owner:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The platform owner account cannot be modified",
        )
    if member.id == admin.id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You cannot disable your own account")
    if member.is_active == payload.is_active:
        return _serialize_member(member)
    if (
        not payload.is_active
        and _is_active_superadmin(member)
        and count_active_superadmins(db, exclude_admin_id=member.id) == 0
    ):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Platform must keep at least one superadmin")
    member.is_active = payload.is_active
    db.add(PlatformAuditLog(
        platform_admin_id=admin.id,
        action="platform_member.activated" if payload.is_active else "platform_member.deactivated",
        description=f"Se {'activó' if payload.is_active else 'desactivó'} la cuenta de {member.email}.",
        details={"member_id": str(member.id)},
    ))
    db.commit()
    db.refresh(member)
    return _serialize_member(member)


@router.post("/team/{member_id}/resend-invitation", response_model=PlatformMemberResponse)
def resend_platform_invitation(
    member_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: PlatformAdmin = Depends(require_platform_permission("platform.team.invite")),
    email_service: EmailService = Depends(get_email_service),
):
    member = _member_or_404(db, member_id)
    if member.hashed_password is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invitation is not pending")
    if not member.is_active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Platform member is disabled")
    invitation_link = _issue_platform_invitation(member)
    db.add(PlatformAuditLog(
        platform_admin_id=admin.id, action="platform_member.invitation_resent",
        description=f"Se generó una nueva invitación para {member.email}.",
        details={"member_id": str(member.id)},
    ))
    db.commit()
    db.refresh(member)
    email_service.send_invitation(
        recipient=member.email, recipient_name=member.full_name,
        invitation_url=invitation_link, tenant_name="Equipo de administración de Flowdesk",
    )
    return _serialize_member(member, invitation_link)


@router.post(
    "/tenants",
    response_model=CreateTenantResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_tenant(
    payload: CreateTenantRequest,
    db: Session = Depends(get_db),
    admin=Depends(require_platform_permission("platform.tenants.create")),
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
    # Cada empresa nueva recibe SUS PROPIOS roles por defecto: Administrador, Miembro y Visor.
    default_roles = create_default_roles(db, tenant.id)
    create_opportunity_stage_templates(db, tenant.id)
    create_product_catalog_templates(db, tenant.id)

    # Crea el primer usuario del tenant como admin, invitado (sin password todavía).
    raw_token = generate_raw_token()
    admin_user = User(
        tenant_id=tenant.id,
        email=payload.admin_email,
        full_name=payload.admin_full_name,
        role_id=default_roles[ADMIN_ROLE_KEY].id,
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
    _admin=Depends(require_platform_permission("platform.tenants.view")),
):
    tenants = db.query(Tenant).order_by(Tenant.created_at.desc()).all()
    return [_serialize_tenant(db, tenant) for tenant in tenants]


def _tenant_or_404(db: Session, tenant_id: uuid.UUID) -> Tenant:
    tenant = TenantRepository().get(db, tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return tenant


@router.get("/tenants/{tenant_id}", response_model=TenantSaaSResponse)
def get_tenant(
    tenant_id: uuid.UUID,
    db: Session = Depends(get_db),
    _admin=Depends(require_platform_permission("platform.tenants.view")),
):
    return _serialize_tenant(db, _tenant_or_404(db, tenant_id))


@router.patch("/tenants/{tenant_id}", response_model=TenantSaaSResponse)
def update_tenant(
    tenant_id: uuid.UUID,
    payload: UpdateTenantRequest,
    db: Session = Depends(get_db),
    admin=Depends(require_platform_permission("platform.tenants.update")),
):
    """Edita el nombre y el identificador (slug) de la empresa."""
    tenant = _tenant_or_404(db, tenant_id)
    existing = TenantRepository().find_by_slug(db, payload.slug)
    if existing and existing.id != tenant.id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slug already in use")

    changes = {}
    if tenant.name != payload.name:
        changes["name"] = {"before": tenant.name, "after": payload.name}
    if tenant.slug != payload.slug:
        changes["slug"] = {"before": tenant.slug, "after": payload.slug}
    tenant.name = payload.name
    tenant.slug = payload.slug
    if changes:
        db.add(PlatformAuditLog(
            platform_admin_id=admin.id, tenant_id=tenant.id, action="tenant.updated",
            description=f"Se actualizaron los datos de {tenant.name}.", details=changes,
        ))
    db.commit()
    db.refresh(tenant)
    return _serialize_tenant(db, tenant)


@router.patch("/tenants/{tenant_id}/status", response_model=TenantSaaSResponse)
def update_tenant_status(
    tenant_id: uuid.UUID,
    payload: UpdateTenantStatusRequest,
    db: Session = Depends(get_db),
    admin=Depends(require_platform_permission("platform.tenants.update")),
):
    """Atajo para habilitar/inhabilitar: inhabilitar equivale a suspender la
    suscripción y bloquea el acceso de todos sus usuarios (login, refresh y
    tokens ya emitidos) sin borrar datos."""
    tenant = _tenant_or_404(db, tenant_id)
    old_status = tenant.subscription_status
    tenant.is_active = payload.is_active
    if payload.is_active and tenant.subscription_status not in ACTIVE_SUBSCRIPTION_STATUSES:
        tenant.subscription_status = "active"
    elif not payload.is_active:
        tenant.subscription_status = "suspended"
    if old_status != tenant.subscription_status:
        verb = "habilitó" if payload.is_active else "inhabilitó"
        db.add(PlatformAuditLog(
            platform_admin_id=admin.id, tenant_id=tenant.id, action="subscription.updated",
            description=f"Se {verb} la empresa {tenant.name}.",
            details={"status": {"before": old_status, "after": tenant.subscription_status}},
        ))
    db.commit()
    db.refresh(tenant)
    return _serialize_tenant(db, tenant)


@router.delete("/tenants/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tenant(
    tenant_id: uuid.UUID,
    confirm_slug: str = Query(..., description="Identificador de la empresa, para confirmar"),
    db: Session = Depends(get_db),
    admin=Depends(require_platform_permission("platform.tenants.delete")),
):
    """Elimina la empresa y TODOS sus datos de forma permanente. Se exige el
    slug como confirmación para evitar borrados accidentales. Las bitácoras de
    auditoría (de plataforma y de la empresa) se conservan."""
    tenant = _tenant_or_404(db, tenant_id)
    if confirm_slug.strip().lower() != tenant.slug:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation slug does not match",
        )

    # El borrado es masivo (no pasa por los eventos del ORM), así que se deja un
    # resumen con cuántos registros se eliminaron de cada tabla, en ambas
    # bitácoras: la de plataforma y la de la propia empresa (que se conserva).
    tenant_repo = TenantRepository()
    details = {
        "tenant_id": str(tenant.id), "tenant_name": tenant.name, "slug": tenant.slug,
        "plan_key": tenant.plan_key, "deleted_records": tenant_repo.count_data(db, tenant.id),
    }
    description = f"Se eliminó la empresa {tenant.name} y todos sus datos."
    db.add(PlatformAuditLog(
        platform_admin_id=admin.id, tenant_id=tenant.id, action="tenant.deleted",
        description=description, details=details, entity="tenants", entity_id=str(tenant.id),
    ))
    record_event(
        db, "tenant.deleted", description, tenant_id=tenant.id, scope="tenant",
        details=details, entity="tenants", entity_id=tenant.id,
    )
    tenant_repo.delete_with_data(db, tenant.id)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/plans", response_model=list[SaaSPlanResponse])
def list_plans(
    db: Session = Depends(get_db),
    _admin=Depends(require_platform_permission("platform.plans.view")),
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


@router.get("/audit", response_model=AuditPageResponse)
def list_platform_audit(
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    operation: list[str] | None = Query(None, description="Repetible: CREATE | UPDATE | DELETE | EVENT"),
    entity: list[str] | None = Query(None, description="Repetible: tabla auditada"),
    admin_id: list[uuid.UUID] | None = Query(None, description="Repetible"),
    tenant_id: uuid.UUID | None = None,
    search: str | None = Query(None, max_length=120),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    db: Session = Depends(get_db),
    _admin=Depends(require_platform_permission("platform.audit.view")),
):
    """Bitácora de acciones de la administración de Flowdesk (paginada)."""
    query = db.query(PlatformAuditLog)
    if tenant_id:
        query = query.filter(PlatformAuditLog.tenant_id == tenant_id)
    query = audit_queries.apply_filters(
        query, PlatformAuditLog, operations=operation, entities=entity, actor_ids=admin_id,
        search=search, date_from=date_from, date_to=date_to,
    )
    items, total = audit_queries.paginate(query, PlatformAuditLog, page, page_size)
    tenant_ids = {item.tenant_id for item in items if item.tenant_id}
    tenants = dict(db.query(Tenant.id, Tenant.name).filter(Tenant.id.in_(tenant_ids)).all()) if tenant_ids else {}
    return AuditPageResponse(
        items=[
            audit_queries.serialize(
                item,
                tenant_name=tenants.get(item.tenant_id) or (item.details or {}).get("tenant_name"),
            )
            for item in items
        ],
        total=total, page=page, page_size=page_size,
    )


@router.get("/audit/report.pdf")
def platform_audit_report(
    operation: list[str] | None = Query(None, description="Repetible: CREATE | UPDATE | DELETE | EVENT"),
    entity: list[str] | None = Query(None, description="Repetible: tabla auditada"),
    admin_id: list[uuid.UUID] | None = Query(None, description="Repetible"),
    tenant_id: uuid.UUID | None = None,
    search: str | None = Query(None, max_length=120),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    tz: str | None = Query(None, max_length=64, description="Zona horaria IANA del usuario"),
    db: Session = Depends(get_db),
    admin: PlatformAdmin = Depends(require_platform_permission("platform.audit.view")),
    _can_export: PlatformAdmin = Depends(require_platform_permission("platform.audit.export")),
):
    """Reporte PDF de la bitácora de plataforma, con los mismos filtros que la pantalla.
    Requiere `platform.audit.view` y `platform.audit.export`."""
    zone = resolve_timezone(tz)
    query = db.query(PlatformAuditLog)
    if tenant_id:
        query = query.filter(PlatformAuditLog.tenant_id == tenant_id)
    query = audit_queries.apply_filters(
        query, PlatformAuditLog, operations=operation, entities=entity, actor_ids=admin_id,
        search=search, date_from=date_from, date_to=date_to,
    )
    items, total = audit_queries.paginate(query, PlatformAuditLog, 1, MAX_REPORT_ROWS)
    tenant_ids = {item.tenant_id for item in items if item.tenant_id}
    tenant_names = dict(db.query(Tenant.id, Tenant.name).filter(Tenant.id.in_(tenant_ids)).all()) if tenant_ids else {}
    filters = audit_queries.describe_filters(
        db, PlatformAuditLog, zone, operations=operation, entities=entity, actor_ids=admin_id,
        search=search, date_from=date_from, date_to=date_to,
        tenant_name=tenant_names.get(tenant_id) if tenant_id else None,
    )
    pdf = build_audit_pdf(
        title="Reporte de auditoría",
        subtitle="Administración de Flowdesk",
        items=items, total=total, filters=filters,
        generated_by=admin.email, tz=zone, show_tenant=True, tenant_names=tenant_names,
    )
    record_event(
        db, "audit.report_exported", f"Generó un reporte de auditoría en PDF ({min(total, MAX_REPORT_ROWS)} registros)",
        scope="platform", details={"filters": dict(filters), "total": total},
    )
    db.commit()

    filename = f"auditoria-plataforma-{datetime.now(zone).strftime('%Y%m%d-%H%M')}.pdf"
    return StreamingResponse(
        pdf, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/audit/filters", response_model=AuditFiltersResponse)
def platform_audit_filters(
    db: Session = Depends(get_db),
    _admin=Depends(require_platform_permission("platform.audit.view")),
):
    return AuditFiltersResponse(
        entities=audit_queries.entity_options(db, PlatformAuditLog),
        actors=audit_queries.actor_options(db, PlatformAuditLog),
    )


@router.get("/subscription-requests", response_model=list[PlanChangeRequestResponse])
def list_subscription_requests(
    db: Session = Depends(get_db),
    _admin=Depends(require_platform_permission("platform.subscriptions.view")),
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
    admin=Depends(require_platform_permission("platform.subscriptions.resolve")),
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
    tenant_id: uuid.UUID,
    payload: UpdateTenantSubscriptionRequest,
    db: Session = Depends(get_db),
    admin=Depends(require_platform_permission("platform.tenants.update")),
):
    tenant = _tenant_or_404(db, tenant_id)
    old_plan_key = tenant.plan_key
    old_status = tenant.subscription_status
    old_billing_email = tenant.billing_email
    plan = get_plan(payload.plan_key)
    tenant.plan_key = payload.plan_key
    tenant.subscription_status = payload.subscription_status
    tenant.is_active = payload.subscription_status in ACTIVE_SUBSCRIPTION_STATUSES
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
