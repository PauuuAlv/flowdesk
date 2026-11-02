from fastapi import Depends, HTTPException, status

from app.models.user import User
from app.security.user_auth import get_current_user
from app.services.access_control import get_user_permission_codes


def require_permission(permission_code: str):
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if permission_code not in get_user_permission_codes(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return dependency
