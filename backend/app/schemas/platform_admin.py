from pydantic import BaseModel, EmailStr


class PlatformAdminLoginRequest(BaseModel):
    email: EmailStr
    password: str


class PlatformAdminTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    # NOTA: a diferencia de User, por ahora PlatformAdmin no tiene refresh token
    # (son pocos usuarios, de ArmSystem, con sesiones más cortas está bien).
    # Si en el futuro hace falta, se agrega igual que en security/jwt.py para User.


class CreateTenantRequest(BaseModel):
    name: str
    slug: str
    admin_email: EmailStr
    admin_full_name: str | None = None


class CreateTenantResponse(BaseModel):
    tenant_id: str
    tenant_name: str
    tenant_slug: str
    admin_user_id: str
    admin_email: str
    # SOLO PARA DESARROLLO: mientras no haya envío de correo real (SES/boto3),
    # regresamos el link de invitación en la respuesta para poder probar el
    # flujo manualmente. ANTES DE PRODUCCIÓN esto debe quitarse y mandarse
    # únicamente por correo — nunca en la respuesta del API.
    dev_invitation_link: str
