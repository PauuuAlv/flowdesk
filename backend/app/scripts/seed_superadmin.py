"""Crea el PlatformAdmin inicial de ArmSystem si todavía no existe.

Uso (dentro del contenedor backend, después de 'alembic upgrade head'):
    python -m app.scripts.seed_superadmin

Es idempotente: si ya existe un PlatformAdmin con SUPERADMIN_EMAIL, no hace nada.
Las credenciales SIEMPRE vienen de variables de entorno (.env), nunca hardcodeadas aquí.
"""

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.platform_admin import PlatformAdmin
from app.security.password import hash_password


def seed_superadmin() -> None:
    db = SessionLocal()
    try:
        existing = (
            db.query(PlatformAdmin)
            .filter(PlatformAdmin.email == settings.SUPERADMIN_EMAIL)
            .first()
        )
        if existing:
            print(f"[seed] PlatformAdmin '{settings.SUPERADMIN_EMAIL}' ya existe, no se crea de nuevo.")
            return

        admin = PlatformAdmin(
            email=settings.SUPERADMIN_EMAIL,
            hashed_password=hash_password(settings.SUPERADMIN_PASSWORD),
            full_name="ArmSystem Superadmin",
            is_active=True,
        )
        db.add(admin)
        db.commit()
        print(f"[seed] PlatformAdmin '{settings.SUPERADMIN_EMAIL}' creado correctamente.")
    finally:
        db.close()


if __name__ == "__main__":
    seed_superadmin()
