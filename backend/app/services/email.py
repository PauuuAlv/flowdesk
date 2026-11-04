import logging
import smtplib
from email.message import EmailMessage
from email.utils import formataddr
from functools import lru_cache
from html import escape
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


class SmtpEmailService:
    """Envía correos transaccionales mediante un servidor SMTP con STARTTLS."""

    def __init__(self) -> None:
        if not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD:
            raise RuntimeError(
                "SMTP_USERNAME and SMTP_PASSWORD are required when EMAIL_PROVIDER=smtp."
            )

    def _send(self, *, recipient: str, subject: str, text: str, html: str) -> None:
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = formataddr(
            (settings.EMAIL_FROM_NAME, settings.EMAIL_FROM_ADDRESS)
        )
        message["To"] = recipient
        message.set_content(text)
        message.add_alternative(html, subtype="html")

        with smtplib.SMTP(
            settings.SMTP_HOST,
            settings.SMTP_PORT,
            timeout=20,
        ) as smtp:
            smtp.ehlo()
            if settings.SMTP_USE_TLS:
                smtp.starttls()
                smtp.ehlo()
            smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            smtp.send_message(message)

    def send_invitation(
        self,
        *,
        recipient: str,
        recipient_name: str | None,
        invitation_url: str,
        tenant_name: str,
    ) -> None:
        greeting = f"Hola {recipient_name}," if recipient_name else "Hola,"
        safe_greeting = escape(greeting)
        safe_tenant_name = escape(tenant_name)
        safe_invitation_url = escape(invitation_url, quote=True)
        self._send(
            recipient=recipient,
            subject=f"Invitación a {tenant_name} en Flowdesk",
            text=(
                f"{greeting}\n\nHas recibido una invitación para unirte a "
                f"{tenant_name} en Flowdesk. Crea tu contraseña desde este enlace:\n\n"
                f"{invitation_url}\n\nEl enlace es personal, temporal y de un solo uso."
            ),
            html=(
                f"<p>{safe_greeting}</p>"
                f"<p>Has recibido una invitación para unirte a <strong>{safe_tenant_name}</strong> "
                "en Flowdesk.</p>"
                f'<p><a href="{safe_invitation_url}">Aceptar invitación</a></p>'
                "<p>El enlace es personal, temporal y de un solo uso.</p>"
            ),
        )

    def send_password_reset(
        self,
        *,
        recipient: str,
        recipient_name: str | None,
        reset_url: str,
    ) -> None:
        greeting = f"Hola {recipient_name}," if recipient_name else "Hola,"
        safe_greeting = escape(greeting)
        safe_reset_url = escape(reset_url, quote=True)
        self._send(
            recipient=recipient,
            subject="Restablece tu contraseña de Flowdesk",
            text=(
                f"{greeting}\n\nRecibimos una solicitud para restablecer tu contraseña. "
                f"Continúa desde este enlace:\n\n{reset_url}\n\n"
                "Si no realizaste esta solicitud, puedes ignorar este mensaje."
            ),
            html=(
                f"<p>{safe_greeting}</p>"
                "<p>Recibimos una solicitud para restablecer tu contraseña.</p>"
                f'<p><a href="{safe_reset_url}">Restablecer contraseña</a></p>'
                "<p>Si no realizaste esta solicitud, puedes ignorar este mensaje.</p>"
            ),
        )

@lru_cache
def get_email_service() -> EmailService:
    provider = settings.EMAIL_PROVIDER.strip().lower()
    if provider == "development":
        return DevelopmentEmailService()
    if provider == "smtp":
        return SmtpEmailService()
    raise RuntimeError(
        f"Unsupported EMAIL_PROVIDER '{settings.EMAIL_PROVIDER}'. "
        "Use 'development' or 'smtp'."
    )
