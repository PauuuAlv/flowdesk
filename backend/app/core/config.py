from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Base de datos
    SQLALCHEMY_DATABASE_URL: str

    # CORS - orígenes permitidos para el frontend
    CORS_ORIGINS: list[str] = ["http://localhost", "http://localhost:4200"]

    # Tokens de autenticación
    JWT_SECRET_KEY: str = "change-me-in-env"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Cuenta inicial de administración de la plataforma
    SUPERADMIN_EMAIL: str
    SUPERADMIN_PASSWORD: str

    # Dirección base para invitaciones y recuperación de contraseña
    FRONTEND_URL: str = "http://localhost"
    INVITATION_TOKEN_EXPIRE_DAYS: int = 7
    RESET_PASSWORD_TOKEN_EXPIRE_HOURS: int = 2

    # Correo transaccional
    EMAIL_PROVIDER: str = "development"
    EMAIL_FROM_ADDRESS: str = "no-reply@flowdesk.local"
    EMAIL_FROM_NAME: str = "Flowdesk"
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_USE_TLS: bool = True
    RESEND_API_KEY: str | None = None
    RESEND_API_URL: str = "https://api.resend.com/emails"

settings = Settings()
