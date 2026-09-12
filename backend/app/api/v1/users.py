from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.schemas.user import InviteUserRequest, InviteUserResponse
from app.security.tokens import generate_raw_token, hash_token
from app.security.user_auth import get_current_admin_user

router = APIRouter()


@router.post("/invite", response_model=InviteUserResponse, status_code=status.HTTP_201_CREATED)
def invite_user(
    payload: InviteUserRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
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

    raw_token = generate_raw_token()
    new_user = User(
        tenant_id=admin.tenant_id,
        email=payload.email,
        full_name=payload.full_name,
        role=payload.role,
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

    # TODO: mandar por correo (SES) en vez de regresarlo en la respuesta.
    invitation_link = f"{settings.FRONTEND_URL}/accept-invite?token={raw_token}"

    return InviteUserResponse(
        user_id=str(new_user.id),
        email=new_user.email,
        role=new_user.role,
        dev_invitation_link=invitation_link,
    )
