import uuid
from datetime import datetime, timedelta, timezone

from jose import jwt, JWTError

from app.core.config import settings

ALGORITHM = settings.JWT_ALGORITHM


def create_access_token(user_id: uuid.UUID, tenant_id: uuid.UUID, role: str) -> str:
    """AC-04 de US-003: el access token debe incluir user_id, tenant_id y roles."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "role": role,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(user_id: uuid.UUID, tenant_id: uuid.UUID) -> str:
    """DECISIÓN DE DISEÑO (US-004, AC-03): refresh token stateless, sin rotación
    ni tabla de revocación todavía. Es la opción más simple para Sprint 1 y
    desbloquea el login end-to-end, pero es deuda técnica reconocida:
    - No se puede invalidar un refresh token antes de que expire (ej. logout real,
      o si se compromete el token) sin una tabla de sesiones/revocación.
    - Antes de producción (o cuando el threat model lo exija) hay que migrar a
      refresh tokens con rotación + tabla `refresh_tokens` para poder revocarlos.
    Coméntenlo entre Developer 1 y Developer 2 y documenten la decisión final
    en el plan (el AC pide explícitamente que el diseño elegido quede documentado)."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "tenant_id": str(tenant_id),
        "type": "refresh",
        "iat": now,
        "exp": now + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=ALGORITHM)

def create_platform_admin_token(admin_id: uuid.UUID) -> str:
    """Token COMPLETAMENTE separado del de los tenant users:
    - type='platform_admin' (nunca 'access'), así un token de superadmin
      jamás puede colarse como si fuera un usuario normal de un tenant.
    - NO lleva tenant_id (a propósito: un PlatformAdmin no pertenece a ninguno).
    - Vida más corta (2h) porque es la cuenta más poderosa del sistema."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(admin_id),
        "type": "platform_admin",
        "iat": now,
        "exp": now + timedelta(hours=2),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=ALGORITHM)



def decode_token(token: str) -> dict:
    """Lanza JWTError si el token es inválido, está mal firmado, o expiró."""
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[ALGORITHM])
