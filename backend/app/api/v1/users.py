import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.models.role import Role
from app.models.tenant import Tenant
from app.schemas.access_control import (
    MessageResponse,
    TenantMemberResponse,
    UpdateMemberRoleRequest,
    UpdateMemberStatusRequest,
)
from app.schemas.user import InviteUserRequest, InviteUserResponse
from app.security.permissions import require_permission
from app.services.email import EmailService, get_email_service
from app.security.tokens import generate_raw_token, hash_token
from app.core.permissions import ADMIN_ROLE_KEY, MEMBER_ROLE_KEY
from app.services.access_control import count_active_admins, get_template_role

router = APIRouter()


def _member_or_404(db: Session, tenant_id, user_id: uuid.UUID) -> User:
    user = db.query(User).filter(User.id == user_id, User.tenant_id == tenant_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


def _member_status(status_value: str) -> str:
    return {"invited": "pending", "disabled": "inactive"}.get(status_value, status_value)


def _serialize_member(user: User) -> TenantMemberResponse:
    role = user.assigned_role
    return TenantMemberResponse(
        id=str(user.id),
        full_name=user.full_name or user.email,
        email=user.email,
        role_id=str(role.id) if role else "",
        role_name=role.name if role else "Sin rol",
        status=_member_status(user.status),
    )


@router.get("", response_model=list[TenantMemberResponse])
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("users.view")),
):
    users = (
        db.query(User)
        .filter(User.tenant_id == current_user.tenant_id)
        .order_by(User.full_name.asc(), User.email.asc())
        .all()
    )
    return [_serialize_member(user) for user in users]


@router.post("/invite", response_model=InviteUserResponse, status_code=status.HTTP_201_CREATED)
def invite_user(
    payload: InviteUserRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_permission("users.invite")),
    email_service: EmailService = Depends(get_email_service),
):
    """Solo un admin puede invitar, y SIEMPRE dentro de su propio tenant
    (admin.tenant_id viene del token, nunca del body — así un admin de un
    tenant jamás puede crear usuarios en el tenant de otra empresa)."""
    existing = (
        db.query(User)
        .filter(User.tenant_id == admin.tenant_id, User.email == payload.email)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists in your tenant",
        )

    if payload.role_id:
        role = (
            db.query(Role)
            .filter(Role.id == payload.role_id, Role.tenant_id == admin.tenant_id)
            .first()
        )
    else:
        role = get_template_role(db, admin.tenant_id, MEMBER_ROLE_KEY)
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    raw_token = generate_raw_token()
    new_user = User(
        tenant_id=admin.tenant_id,
        email=payload.email,
        full_name=payload.full_name,
        role_id=role.id,
        status="invited",
        hashed_password=None,
        invited_by_user_id=admin.id,
        invitation_token_hash=hash_token(raw_token),
        invitation_expires_at=datetime.now(timezone.utc)
        + timedelta(days=settings.INVITATION_TOKEN_EXPIRE_DAYS),
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    invitation_link = f"{settings.FRONTEND_URL}/accept-invite?token={raw_token}"
    tenant = db.query(Tenant).filter(Tenant.id == admin.tenant_id).first()
    email_service.send_invitation(
        recipient=new_user.email,
        recipient_name=new_user.full_name,
        invitation_url=invitation_link,
        tenant_name=tenant.name if tenant else "Flowdesk",
    )

    return InviteUserResponse(
        user_id=str(new_user.id),
        email=new_user.email,
        role=role.template_key or "custom",
        role_id=str(role.id),
        role_name=role.name,
        dev_invitation_link=invitation_link,
    )


@router.patch("/{user_id}/role", response_model=TenantMemberResponse)
def update_user_role(
    user_id: uuid.UUID,
    payload: UpdateMemberRoleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("users.update")),
):
    user = _member_or_404(db, current_user.tenant_id, user_id)
    try:
        role_id = uuid.UUID(payload.role_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid role id")
    role = db.query(Role).filter(Role.id == role_id, Role.tenant_id == current_user.tenant_id).first()
    if not role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You cannot change your own role")
    # Nunca dejar a la empresa sin al menos un Administrador activo.
    if (
        user.role_key == ADMIN_ROLE_KEY
        and role.template_key != ADMIN_ROLE_KEY
        and user.status == "active"
        and count_active_admins(db, current_user.tenant_id, exclude_user_id=user.id) == 0
    ):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tenant must keep at least one admin")
    user.role_id = role.id
    db.commit()
    db.refresh(user)
    return _serialize_member(user)


@router.patch("/{user_id}/status", response_model=TenantMemberResponse)
def update_user_status(
    user_id: uuid.UUID,
    payload: UpdateMemberStatusRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("users.delete")),
):
    user = _member_or_404(db, current_user.tenant_id, user_id)
    if user.id == current_user.id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You cannot disable your own account")
    if user.status == "invited":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Pending invitation cannot change status")
    if (
        payload.status == "inactive"
        and user.role_key == ADMIN_ROLE_KEY
        and count_active_admins(db, current_user.tenant_id, exclude_user_id=user.id) == 0
    ):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tenant must keep at least one admin")
    user.status = "active" if payload.status == "active" else "disabled"
    db.commit()
    db.refresh(user)
    return _serialize_member(user)


@router.post("/{user_id}/resend-invitation", response_model=MessageResponse)
def resend_invitation(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("users.invite")),
    email_service: EmailService = Depends(get_email_service),
):
    user = _member_or_404(db, current_user.tenant_id, user_id)
    if user.status != "invited":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invitation is not pending")
    raw_token = generate_raw_token()
    user.invitation_token_hash = hash_token(raw_token)
    user.invitation_expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.INVITATION_TOKEN_EXPIRE_DAYS
    )
    db.commit()
    invitation_link = f"{settings.FRONTEND_URL}/accept-invite?token={raw_token}"
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    email_service.send_invitation(
        recipient=user.email,
        recipient_name=user.full_name,
        invitation_url=invitation_link,
        tenant_name=tenant.name if tenant else "Flowdesk",
    )
    return MessageResponse(message="Invitation generated successfully")
