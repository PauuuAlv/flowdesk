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
        role_name=role.name if role else user.role.capitalize(),
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

    role = None
    if payload.role_id:
        role = (
            db.query(Role)
            .filter(Role.id == payload.role_id, Role.tenant_id == admin.tenant_id)
            .first()
        )
        if not role:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    else:
        role = (
            db.query(Role)
            .filter(Role.tenant_id == admin.tenant_id, Role.template_key == payload.role)
            .first()
        )

    raw_token = generate_raw_token()
    new_user = User(
        tenant_id=admin.tenant_id,
        email=payload.email,
        full_name=payload.full_name,
        role=payload.role,
        role_id=role.id if role else None,
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
        role=new_user.role,
        role_id=str(role.id) if role else None,
        role_name=role.name if role else new_user.role.capitalize(),
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
    user.role_id = role.id
    user.role = role.template_key or "custom"
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
