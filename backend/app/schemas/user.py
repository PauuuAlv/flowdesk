from typing import Literal

from pydantic import BaseModel, EmailStr


class InviteUserRequest(BaseModel):
    email: EmailStr
    full_name: str | None = None
    # Un admin puede invitar a otro admin o a un member, pero nunca a un
    # platform_admin (ese rol ni siquiera existe en este modelo, ver User).
    role: Literal["admin", "member"] = "member"


class InviteUserResponse(BaseModel):
    user_id: str
    email: str
    role: str
    # SOLO DEV, igual que en platform_admin: mientras no haya envío de correo
    # real, regresamos el link aquí para poder probar. Quitar antes de prod.
    dev_invitation_link: str

class UserMeResponse(BaseModel):
    id: str
    tenant_id: str
    email: str
    full_name: str | None
    role: str
    status: str
