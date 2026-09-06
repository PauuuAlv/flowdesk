import uuid

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User

# Igual que en platform_admin_auth.py: esto NO vuelve a validar el token
# (eso ya lo hizo TenantContextMiddleware antes de llegar aquí). Solo existe
# para que FastAPI genere el esquema de seguridad y Swagger muestre el
# botón "Authorize" en estos endpoints.
bearer_scheme = HTTPBearer()


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    _credentials=Depends(bearer_scheme),
) -> User:
    """Lee user_id/tenant_id de request.state, que el middleware ya dejó ahí
    después de validar el JWT. Si llegamos aquí sin esos datos, algo está
    mal configurado (esta ruta debería estar protegida por el middleware)."""
    user_id = getattr(request.state, "user_id", None)
    tenant_id = getattr(request.state, "tenant_id", None)

    if not user_id or not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    user = (
        db.query(User)
        .filter(User.id == uuid.UUID(user_id), User.tenant_id == uuid.UUID(tenant_id))
        .first()
    )
    if not user or user.status != "active":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    return user


def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Para endpoints que solo el admin de un tenant puede usar (como invitar
    gente nueva). Un 'member' recibe 403, no 401 (sí está autenticado,
    solo no tiene permiso)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin role required")
    return current_user
