import logging
from functools import lru_cache
from typing import Protocol

from app.core.config import settings

logger = logging.getLogger("flowdesk.email")


class EmailService(Protocol):
    """Contrato independiente del proveedor de correo transaccional."""

    def send_invitation(
        self,
        *,
        recipient: str,
        recipient_name: str | None,
        invitation_url: str,
        tenant_name: str,
    ) -> None: ...

    def send_password_reset(
        self,
        *,
        recipient: str,
        recipient_name: str | None,
        reset_url: str,
    ) -> None: ...


class DevelopmentEmailService:
    """No envía mensajes: deja los enlaces visibles únicamente en logs locales."""

    def send_invitation(
        self,
        *,
        recipient: str,
        recipient_name: str | None,
        invitation_url: str,
        tenant_name: str,
    ) -> None:
        logger.warning(
            "[EMAIL DEVELOPMENT] invitation recipient=%s name=%s tenant=%s url=%s",
            recipient,
            recipient_name or "",
            tenant_name,
            invitation_url,
        )

    def send_password_reset(
        self,
        *,
        recipient: str,
        recipient_name: str | None,
        reset_url: str,
    ) -> None:
        logger.warning(
            "[EMAIL DEVELOPMENT] password_reset recipient=%s name=%s url=%s",
            recipient,
            recipient_name or "",
            reset_url,
        )


@lru_cache
def get_email_service() -> EmailService:
    provider = settings.EMAIL_PROVIDER.strip().lower()
    if provider == "development":
        return DevelopmentEmailService()
    raise RuntimeError(
        f"Unsupported EMAIL_PROVIDER '{settings.EMAIL_PROVIDER}'. "
        "Configure 'development' until a production provider is selected."
    )
