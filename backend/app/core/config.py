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

    # Archivos locales en desarrollo. En producción este servicio puede
    # sustituirse por un adaptador S3/R2 sin guardar binarios en PostgreSQL.
    MEDIA_ROOT: str = "/app/storage"

    # Web Push (estándar W3C Push API + VAPID, RFC 8292). Genera el par de
    # claves con `python -m app.scripts.generate_vapid_keys`. Sin claves, la
    # API sigue funcionando y las notificaciones solo se ven dentro del panel.
    VAPID_PUBLIC_KEY: str | None = None
    VAPID_PRIVATE_KEY: str | None = None
    # Contacto del operador para los servicios push (mailto: o https:).
    VAPID_SUBJECT: str = "mailto:no-reply@flowdesk.local"
    # Despachador en segundo plano: dispara recordatorios de actividades y
    # envía los avisos pendientes. El intervalo define la precisión de los
    # recordatorios.
    PUSH_WORKER_ENABLED: bool = True
    PUSH_SCAN_INTERVAL_SECONDS: int = 60
    # Notificaciones más antiguas que esto ya no se envían al navegador.
    PUSH_MAX_AGE_HOURS: int = 12
    # Tiempo que el servicio push conserva el mensaje si el equipo está apagado.
    PUSH_TTL_SECONDS: int = 86400

    @property
    def push_enabled(self) -> bool:
        return bool(self.VAPID_PUBLIC_KEY and self.VAPID_PRIVATE_KEY)

settings = Settings()
