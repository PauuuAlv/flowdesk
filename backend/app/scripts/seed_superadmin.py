"""Crea el primer Superadministrador de ArmSystem si todavía no existe.

Uso (dentro del contenedor backend, después de 'alembic upgrade head'):
    python -m app.scripts.seed_superadmin

Es idempotente: si ya existe un PlatformAdmin con SUPERADMIN_EMAIL, se asegura
de que sea la cuenta principal (Superadministrador activo que nadie puede
cambiar de rol ni desactivar) y no crea nada más. Después, ese
superadministrador puede invitar a más integrantes (incluidos otros
superadministradores) desde "Equipo de plataforma".
Las credenciales SIEMPRE vienen de variables de entorno (.env), nunca hardcodeadas aquí.
"""

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.platform_permissions import SUPERADMIN_ROLE_KEY
from app.models.platform_admin import PlatformAdmin
from app.security.password import hash_password
from app.services.platform_access import get_platform_template_role, sync_platform_access


def seed_superadmin() -> None:
    db = SessionLocal()
    try:
        # Garantiza que existan los permisos y roles por defecto de plataforma.
        sync_platform_access(db)
        superadmin_role = get_platform_template_role(db, SUPERADMIN_ROLE_KEY)

        existing = (
            db.query(PlatformAdmin)
            .filter(PlatformAdmin.email == settings.SUPERADMIN_EMAIL)
            .first()
        )
        if existing:
            # sync_platform_access ya la marcó como cuenta principal (Superadministrador activo).
            print(f"[seed] PlatformAdmin '{settings.SUPERADMIN_EMAIL}' ya existe, no se crea de nuevo.")
            return

        admin = PlatformAdmin(
            email=settings.SUPERADMIN_EMAIL,
            hashed_password=hash_password(settings.SUPERADMIN_PASSWORD),
            full_name="ArmSystem Superadmin",
            is_active=True,
            is_owner=True,
            role_id=superadmin_role.id,
        )
        db.add(admin)
        db.commit()
        print(f"[seed] PlatformAdmin '{settings.SUPERADMIN_EMAIL}' creado correctamente.")
    finally:
        db.close()


if __name__ == "__main__":
    seed_superadmin()
