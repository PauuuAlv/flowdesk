import logging
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.audit import record_event
from app.core.audit_context import get_audit_context
from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.models.tenant import Tenant
from app.repositories.user_repository import UserRepository
from app.repositories.password_reset_repository import PasswordResetRepository
from app.repositories.tenant_repository import TenantRepository
from app.schemas.auth import (
    LoginRequest,
    TokenResponse,
    RefreshRequest,
    RegisterRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    MessageResponse,
    UpdateProfileRequest,
    ChangePasswordRequest,
)
from app.schemas.user import UserMeResponse
from app.security.password import verify_password, hash_password
from app.security.jwt import create_access_token, create_refresh_token, decode_token
from app.security.tokens import generate_raw_token, hash_token
from app.security.user_auth import get_current_user
from app.services.access_control import get_user_permission_codes
from app.services.email import EmailService, get_email_service

router = APIRouter()
logger = logging.getLogger("flowdesk.auth")


def _record_failed_login(db: Session, user: User, email: str, reason: str) -> None:
    """Intento fallido sobre una cuenta existente: queda en la auditoría de su
    empresa (los correos que no existen no se registran)."""
    entry = record_event(
        db, "auth.login_failed", f"Intento de inicio de sesión fallido para {email}",
        tenant_id=user.tenant_id, scope="tenant", entity="users", entity_id=user.id,
        details={"reason": reason},
    )
    entry.actor_type = "anonymous"
    entry.actor_email = email
    db.commit()


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
            if user:
                _record_failed_login(db, user, payload.email, f"status:{user.status}")
            raise invalid_credentials

    if not user or not verify_password(payload.password, user.hashed_password):
        _record_failed_login(db, user, payload.email, "wrong_password")
        raise invalid_credentials

    # Solo se revela que la empresa está inhabilitada (suscripción suspendida o
    # cancelada) después de validar la contraseña.
    if not TenantRepository().is_active(db, user.tenant_id):
        _record_failed_login(db, user, payload.email, "company_disabled")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Company disabled")

    get_audit_context().set_user(user.id, user.tenant_id, user.email)
    record_event(
        db, "auth.login", f"{user.email} inició sesión",
        tenant_id=user.tenant_id, entity="users", entity_id=user.id,
    )
    db.commit()

    access_token = create_access_token(user_id=user.id, tenant_id=user.tenant_id, role=user.role_key)
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
    if not TenantRepository().is_active(db, user.tenant_id):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Company disabled")

    # NOTA: como el refresh token no rota (ver security/jwt.py), aquí solo
    # emitimos un access_token nuevo y reusamos el mismo refresh_token.
    # Si más adelante implementan rotación, aquí es donde se generaría
    # un refresh_token nuevo y se invalidaría el anterior.
    access_token = create_access_token(user_id=user.id, tenant_id=user.tenant_id, role=user.role_key)

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

    if not TenantRepository().is_active(db, user.tenant_id):
        raise invalid_token

    if user.invitation_expires_at is None or user.invitation_expires_at < datetime.now(timezone.utc):
        raise invalid_token

    # Registro público (aceptar invitación): el cambio se atribuye al propio
    # usuario que se está registrando.
    get_audit_context().set_user(user.id, user.tenant_id, user.email)
    user.hashed_password = hash_password(payload.password)
    user.status = "active"
    user.activated_at = datetime.now(timezone.utc)
    # Se limpia el token: de un solo uso, no se puede reusar después de activarse.
    user.invitation_token_hash = None
    user.invitation_expires_at = None
    record_event(
        db, "auth.register", f"{user.email} aceptó su invitación y activó su cuenta",
        tenant_id=user.tenant_id, entity="users", entity_id=user.id,
    )

    db.commit()
    db.refresh(user)

    access_token = create_access_token(user_id=user.id, tenant_id=user.tenant_id, role=user.role_key)
    refresh_token = create_refresh_token(user_id=user.id, tenant_id=user.tenant_id)

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)

@router.get("/me", response_model=UserMeResponse)
def get_me(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Devuelve la identidad de quien está haciendo la request, a partir
    únicamente del token — nunca de un parámetro que mande el cliente."""
    return _me_response(db, current_user)


@router.patch("/me", response_model=UserMeResponse)
def update_me(
    payload: UpdateProfileRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cada usuario puede cambiar su propio nombre (no su correo, rol ni estado)."""
    current_user.full_name = payload.full_name
    db.commit(); db.refresh(current_user)
    return _me_response(db, current_user)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    payload: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cambio de contraseña con la sesión iniciada: exige la contraseña actual."""
    if not current_user.hashed_password or not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
    if verify_password(payload.new_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New password must be different")
    current_user.hashed_password = hash_password(payload.new_password)
    record_event(
        db, "auth.password_changed", f"{current_user.email} cambió su contraseña",
        tenant_id=current_user.tenant_id, entity="users", entity_id=current_user.id,
    )
    db.commit()
    logger.info("User %s changed their password", current_user.id)


def _me_response(db: Session, current_user: User) -> UserMeResponse:
    tenant = db.query(Tenant).filter(Tenant.id == current_user.tenant_id).first()
    return UserMeResponse(
        id=str(current_user.id),
        tenant_id=str(current_user.tenant_id),
        tenant_name=tenant.name if tenant else "Empresa",
        tenant_logo_url=tenant.logo_url if tenant else None,
        tenant_currency=(tenant.currency if tenant else None) or "MXN",
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role_key,
        role_id=str(current_user.role_id),
        role_name=current_user.assigned_role.name if current_user.assigned_role else None,
        permissions=get_user_permission_codes(current_user),
        status=current_user.status,
    )

@router.post("/forgot-password", response_model=MessageResponse)
def forgot_password(
    payload: ForgotPasswordRequest,
    db: Session = Depends(get_db),
    email_service: EmailService = Depends(get_email_service),
):
    """SIEMPRE responde el mismo mensaje genérico, exista o no el email.
    Si reveláramos 'ese email no existe', cualquiera podría usar este endpoint
    para averiguar qué correos están registrados (enumeración de usuarios)."""
    generic_response = MessageResponse(
        message="If that email is registered, we've sent password reset instructions."
    )

    user_repo = UserRepository(db)
    user = user_repo.find_by_email_any_tenant(db, payload.email)

    if not user or user.status != "active" or not TenantRepository().is_active(db, user.tenant_id):
        return generic_response  # no seguimos, pero tampoco lo decimos

    entry = record_event(
        db, "auth.password_reset_requested",
        f"Se solicitó restablecer la contraseña de {user.email}",
        tenant_id=user.tenant_id, scope="tenant", entity="users", entity_id=user.id,
    )
    entry.actor_type = "anonymous"
    entry.actor_email = user.email

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

    reset_link = f"{settings.FRONTEND_URL}/reset-password?token={raw_token}"
    try:
        email_service.send_password_reset(
            recipient=user.email,
            recipient_name=user.full_name,
            reset_url=reset_link,
        )
    except Exception:
        # La respuesta sigue siendo genérica para no revelar si el correo existe.
        logger.exception("Password reset email delivery failed")

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
    if not user or user.status != "active" or not TenantRepository().is_active(db, user.tenant_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    get_audit_context().set_user(user.id, user.tenant_id, user.email)
    user.hashed_password = hash_password(payload.new_password)
    reset_row.used_at = datetime.now(timezone.utc)
    record_event(
        db, "auth.password_reset", f"{user.email} restableció su contraseña con un enlace de recuperación",
        tenant_id=user.tenant_id, entity="users", entity_id=user.id,
    )
    db.commit()

    # Por si el usuario había pedido varios links de reset, invalida los demás.
    reset_repo.invalidate_all_for_user(db, user.id)

    return MessageResponse(message="Password updated successfully.")
