import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.audit_context import get_audit_context
from app.core.database import get_db
from app.core.platform_permissions import PLATFORM_PERMISSION_CODES
from app.models.platform_admin import PlatformAdmin
from app.security.jwt import decode_token

# Usar HTTPBearer (en vez de leer el header a mano) es lo que hace que FastAPI
# genere el esquema de seguridad en el OpenAPI/Swagger, y por lo tanto aparezca
# el botón "Authorize" para poder probar estos endpoints desde /docs.
bearer_scheme = HTTPBearer()


def get_current_platform_admin(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> PlatformAdmin:
    token = credentials.credentials
    try:
        payload = decode_token(token)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    if payload.get("type") != "platform_admin":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    admin = db.query(PlatformAdmin).filter(PlatformAdmin.id == uuid.UUID(payload["sub"])).first()
    if not admin or not admin.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin not found or inactive")

    get_audit_context().set_platform_admin(admin.id, admin.email)
    return admin


def require_platform_permission(permission_code: str):
    """Igual que `require_permission` de los tenants, pero para el equipo de
    plataforma: el permiso debe estar en el rol de plataforma de la cuenta."""
    if permission_code not in PLATFORM_PERMISSION_CODES:  # error de programación
        raise ValueError(f"Unknown platform permission: {permission_code}")

    def dependency(admin: PlatformAdmin = Depends(get_current_platform_admin)) -> PlatformAdmin:
        if permission_code not in admin.permission_codes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient platform permissions",
            )
        return admin

    return dependency
