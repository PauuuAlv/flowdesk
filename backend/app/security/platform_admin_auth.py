import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.database import get_db
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

    return admin