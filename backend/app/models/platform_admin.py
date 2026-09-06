from sqlalchemy import Column, String, Boolean

from app.models.base import BaseModel


class PlatformAdmin(BaseModel):
    """Personal de ArmSystem que administra el SaaS completo.

    A PROPÓSITO no hereda TenantMixin: un PlatformAdmin no pertenece a
    ningún tenant, administra TODOS. Por eso vive en su propia tabla y
    nunca se mezcla con la tabla `users` (que sí exige tenant_id NOT NULL
    en todo momento — ver TenantMixin en base.py).

    El primer registro de esta tabla se crea vía seed automático al
    desplegar la base de datos (ver app/scripts/seed_superadmin.py),
    nunca por un endpoint público de registro.
    """

    __tablename__ = "platform_admins"

    email = Column(String(255), nullable=False, unique=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
