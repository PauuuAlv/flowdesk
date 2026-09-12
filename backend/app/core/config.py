from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Base de datos
    SQLALCHEMY_DATABASE_URL: str

    # CORS - orígenes permitidos para el frontend
    CORS_ORIGINS: list[str] = ["http://localhost", "http://localhost:4200"]

    # JWT (se usará en Sprint 1 - Semana 2 para login/refresh)
    JWT_SECRET_KEY: str = "change-me-in-env"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Seed del PlatformAdmin inicial (ver app/scripts/seed_superadmin.py).
    # OBLIGATORIO definirlas en .env antes de correr el seed — nunca
    # hardcodear una contraseña por defecto aquí.
    SUPERADMIN_EMAIL: str
    SUPERADMIN_PASSWORD: str

    # Base del link que se manda en invitaciones y reset de password.
    # En dev es el nginx local; en prod será el dominio real.
    FRONTEND_URL: str = "http://localhost"
    INVITATION_TOKEN_EXPIRE_DAYS: int = 7
    RESET_PASSWORD_TOKEN_EXPIRE_HOURS: int = 2

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
