from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    # IMPORTANTE (US-005 AC-02): tenant_id NUNCA se acepta aquí desde el cliente.
    # ¿Cómo sabemos a qué tenant pertenece el login? Dos opciones válidas:
    #   a) el email es único globalmente (no compuesto por tenant) -> se busca
    #      el user por email en todos los tenants
    #   b) se resuelve el tenant por subdominio/dominio de la petición
    # Como el modelo User quedó con email único POR TENANT (no global), hace
    # falta definir esto con tu compañero antes de continuar. Ver nota en auth.py.


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str

class RegisterRequest(BaseModel):
    """Para ACEPTAR una invitación existente, no para auto-registro
    (recuerda: el modelo de negocio es 100% por invitación)."""
    token: str
    password: str = Field(min_length=8)

class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8)


class MessageResponse(BaseModel):
    message: str
