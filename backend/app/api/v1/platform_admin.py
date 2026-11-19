import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.repositories.platform_admin_repository import PlatformAdminRepository
from app.repositories.tenant_repository import TenantRepository
from app.schemas.platform_admin import (
    PlatformAdminLoginRequest,
    PlatformAdminTokenResponse,
    CreateTenantRequest,
    CreateTenantResponse,
    TenantSummary,
    UpdateTenantRequest,
    UpdateTenantStatusRequest,
)
from app.security.jwt import create_platform_admin_token
from app.security.password import verify_password
from app.security.platform_admin_auth import get_current_platform_admin
from app.security.tokens import generate_raw_token, hash_token
from app.core.permissions import ADMIN_ROLE_KEY
from app.services.access_control import create_default_roles
from app.services.email import EmailService, get_email_service

router = APIRouter()


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

    tenant = tenant_repo.create(db, name=payload.name, slug=payload.slug)
    # Cada empresa nueva recibe SUS PROPIOS roles por defecto: Administrador, Miembro y Visor.
    default_roles = create_default_roles(db, tenant.id)

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
        dev_invitation_link=invitation_link,
    )


def _tenant_or_404(db: Session, tenant_id: uuid.UUID):
    tenant = TenantRepository().get(db, tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return tenant


def _summary_for(db: Session, tenant_id: uuid.UUID) -> TenantSummary:
    for row in TenantRepository().list_with_stats(db):
        if row["tenant"].id == tenant_id:
            return _to_summary(row)
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")


def _to_summary(row: dict) -> TenantSummary:
    tenant = row["tenant"]
    admin = row["admin"]
    return TenantSummary(
        id=str(tenant.id),
        name=tenant.name,
        slug=tenant.slug,
        is_active=bool(tenant.is_active),
        created_at=tenant.created_at,
        admin_email=admin.email if admin else None,
        admin_full_name=admin.full_name if admin else None,
        users_count=row["users_count"],
        active_users_count=row["active_users_count"],
    )


@router.get("/tenants", response_model=list[TenantSummary])
def list_tenants(
    db: Session = Depends(get_db),
    _admin=Depends(get_current_platform_admin),
):
    return [_to_summary(row) for row in TenantRepository().list_with_stats(db)]


@router.get("/tenants/{tenant_id}", response_model=TenantSummary)
def get_tenant(
    tenant_id: uuid.UUID,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_platform_admin),
):
    return _summary_for(db, tenant_id)


@router.patch("/tenants/{tenant_id}", response_model=TenantSummary)
def update_tenant(
    tenant_id: uuid.UUID,
    payload: UpdateTenantRequest,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_platform_admin),
):
    tenant = _tenant_or_404(db, tenant_id)
    existing = TenantRepository().find_by_slug(db, payload.slug)
    if existing and existing.id != tenant.id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slug already in use")

    tenant.name = payload.name
    tenant.slug = payload.slug
    db.commit()
    return _summary_for(db, tenant_id)


@router.patch("/tenants/{tenant_id}/status", response_model=TenantSummary)
def update_tenant_status(
    tenant_id: uuid.UUID,
    payload: UpdateTenantStatusRequest,
    db: Session = Depends(get_db),
    _admin=Depends(get_current_platform_admin),
):
    """Inhabilitar una empresa bloquea el acceso de todos sus usuarios
    (login, refresh y cualquier request con un token ya emitido) sin borrar datos."""
    tenant = _tenant_or_404(db, tenant_id)
    tenant.is_active = payload.is_active
    db.commit()
    return _summary_for(db, tenant_id)


@router.delete("/tenants/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tenant(
    tenant_id: uuid.UUID,
    confirm_slug: str = Query(..., description="Identificador de la empresa, para confirmar"),
    db: Session = Depends(get_db),
    _admin=Depends(get_current_platform_admin),
):
    """Elimina la empresa y TODOS sus datos de forma permanente. Se exige el
    slug como confirmación para evitar borrados accidentales."""
    tenant = _tenant_or_404(db, tenant_id)
    if confirm_slug.strip().lower() != tenant.slug:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation slug does not match",
        )

    TenantRepository().delete_with_data(db, tenant.id)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
