import uuid
from pydantic import BaseModel, EmailStr, Field


class InviteUserRequest(BaseModel):
    email: EmailStr
    full_name: str | None = None
    # Rol del tenant que tendra el invitado. Si no se manda, se usa "Miembro".
    role_id: uuid.UUID | None = None


class InviteUserResponse(BaseModel):
    user_id: str
    email: str
    role: str
    role_id: str | None = None
    role_name: str | None = None
    # SOLO DEV, igual que en platform_admin: mientras no haya envío de correo
    # real, regresamos el link aquí para poder probar. Quitar antes de prod.
    dev_invitation_link: str

class UserMeResponse(BaseModel):
    id: str
    tenant_id: str
    tenant_name: str
    email: str
    full_name: str | None
    role: str
    role_id: str | None = None
    role_name: str | None = None
    permissions: list[str] = Field(default_factory=list)
    status: str
