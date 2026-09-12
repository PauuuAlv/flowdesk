from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
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
)
from app.security.jwt import create_platform_admin_token
from app.security.password import verify_password
from app.security.platform_admin_auth import get_current_platform_admin
from app.security.tokens import generate_raw_token, hash_token

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
):
    tenant_repo = TenantRepository()

    if tenant_repo.find_by_slug(db, payload.slug):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Slug already in use")

    tenant = tenant_repo.create(db, name=payload.name, slug=payload.slug)

    # Crea el primer usuario del tenant como admin, invitado (sin password todavía).
    raw_token = generate_raw_token()
    admin_user = User(
        tenant_id=tenant.id,
        email=payload.admin_email,
        full_name=payload.admin_full_name,
        role="admin",
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

    # TODO: mandar este link por correo (boto3/SES, MAIL_FROM ya está en .env)
    # en vez de regresarlo en la respuesta. Ver nota en schemas/platform_admin.py.
    invitation_link = f"{settings.FRONTEND_URL}/accept-invite?token={raw_token}"

    return CreateTenantResponse(
        tenant_id=str(tenant.id),
        tenant_name=tenant.name,
        tenant_slug=tenant.slug,
        admin_user_id=str(admin_user.id),
        admin_email=admin_user.email,
        dev_invitation_link=invitation_link,
    )
