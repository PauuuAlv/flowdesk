import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.repositories.password_reset_repository import PasswordResetRepository
from app.schemas.auth import (
    LoginRequest,
    TokenResponse,
    RefreshRequest,
    RegisterRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    MessageResponse,
)
from app.schemas.user import UserMeResponse
from app.security.password import verify_password, hash_password
from app.security.jwt import create_access_token, create_refresh_token, decode_token
from app.security.tokens import generate_raw_token, hash_token
from app.security.user_auth import get_current_user

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user_repo = UserRepository(db)
    user = user_repo.find_by_email_any_tenant(db, payload.email)

    # AC-03 de US-003: mismo error para "no existe" y "password incorrecto",
    # para no revelar si el email está registrado.
    invalid_credentials = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid email or password",
    )

    if not user or user.status != "active" or not user.hashed_password:
            # Cubre: usuario no existe, todavía está 'invited' (sin password), o 'disabled'.
            raise invalid_credentials
    
    if not user or not verify_password(payload.password, user.hashed_password):
        raise invalid_credentials

    access_token = create_access_token(user_id=user.id, tenant_id=user.tenant_id, role=user.role)
    refresh_token = create_refresh_token(user_id=user.id, tenant_id=user.tenant_id)

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    try:
        data = decode_token(payload.refresh_token)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token")

    if data.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    user_repo = UserRepository(db)
    user = user_repo.get(tenant_id=uuid.UUID(data["tenant_id"]), id=uuid.UUID(data["sub"]))
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    # NOTA: como el refresh token no rota (ver security/jwt.py), aquí solo
    # emitimos un access_token nuevo y reusamos el mismo refresh_token.
    # Si más adelante implementan rotación, aquí es donde se generaría
    # un refresh_token nuevo y se invalidaría el anterior.
    access_token = create_access_token(user_id=user.id, tenant_id=user.tenant_id, role=user.role)

    return TokenResponse(access_token=access_token, refresh_token=payload.refresh_token)

@router.post("/register", response_model=TokenResponse)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    """Acepta una invitación existente: valida el token, define la contraseña,
    activa al usuario, y de una vez lo deja logueado (regresa tokens),
    para no obligarlo a hacer login por separado justo después."""
    user_repo = UserRepository(db)
    token_hash = hash_token(payload.token)
    user = user_repo.find_by_invitation_token_hash(db, token_hash)

    invalid_token = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid or expired invitation token",
    )

    if not user or user.status != "invited":
        raise invalid_token

    if user.invitation_expires_at is None or user.invitation_expires_at < datetime.now(timezone.utc):
        raise invalid_token

    user.hashed_password = hash_password(payload.password)
    user.status = "active"
    user.activated_at = datetime.now(timezone.utc)
    # Se limpia el token: de un solo uso, no se puede reusar después de activarse.
    user.invitation_token_hash = None
    user.invitation_expires_at = None

    db.commit()
    db.refresh(user)

    access_token = create_access_token(user_id=user.id, tenant_id=user.tenant_id, role=user.role)
    refresh_token = create_refresh_token(user_id=user.id, tenant_id=user.tenant_id)

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)

@router.get("/me", response_model=UserMeResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Devuelve la identidad de quien está haciendo la request, a partir
    únicamente del token — nunca de un parámetro que mande el cliente."""
    return UserMeResponse(
        id=str(current_user.id),
        tenant_id=str(current_user.tenant_id),
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        status=current_user.status,
    )

@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """SIEMPRE responde el mismo mensaje genérico, exista o no el email.
    Si reveláramos 'ese email no existe', cualquiera podría usar este endpoint
    para averiguar qué correos están registrados (enumeración de usuarios)."""
    generic_response = MessageResponse(
        message="If that email is registered, we've sent password reset instructions."
    )

    user_repo = UserRepository(db)
    user = user_repo.find_by_email_any_tenant(db, payload.email)

    if not user or user.status != "active":
        return generic_response  # no seguimos, pero tampoco lo decimos

    raw_token = generate_raw_token()
    reset_repo = PasswordResetRepository()
    reset_repo.create(
        db,
        tenant_id=user.tenant_id,
        user_id=user.id,
        token_hash=hash_token(raw_token),
        expires_at=datetime.now(timezone.utc)
        + timedelta(hours=settings.RESET_PASSWORD_TOKEN_EXPIRE_HOURS),
    )

    # TODO: mandar por correo (SES) en vez de solo loguearlo/regresarlo.
    reset_link = f"{settings.FRONTEND_URL}/reset-password?token={raw_token}"
    print(f"[DEV] Password reset link for {user.email}: {reset_link}")  # visible en docker logs

    return generic_response


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    reset_repo = PasswordResetRepository()
    token_hash = hash_token(payload.token)
    reset_row = reset_repo.find_valid_by_token_hash(db, token_hash)

    if not reset_row:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    user_repo = UserRepository(db)
    user = user_repo.get(tenant_id=reset_row.tenant_id, id=reset_row.user_id)
    if not user or user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    user.hashed_password = hash_password(payload.new_password)
    reset_row.used_at = datetime.now(timezone.utc)
    db.commit()

    # Por si el usuario había pedido varios links de reset, invalida los demás.
    reset_repo.invalidate_all_for_user(db, user.id)

    return MessageResponse(message="Password updated successfully.")
