import logging
import json
import smtplib
from email.message import EmailMessage
from email.utils import formataddr
from functools import lru_cache
from html import escape
from dataclasses import dataclass
from typing import Protocol
import base64
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.config import settings

logger = logging.getLogger("flowdesk.email")


@dataclass(frozen=True)
class EmailAttachment:
    filename: str
    content: bytes
    mime_type: str = "application/pdf"


@dataclass(frozen=True)
class EmailAddress:
    email: str
    name: str | None = None

    def formatted(self) -> str:
        return formataddr((self.name or "", self.email))


class EmailService(Protocol):
    """Contrato independiente del proveedor de correo transaccional."""

    def send_quote(
        self,
        *,
        sender: EmailAddress,
        recipient: EmailAddress,
        subject: str,
        text: str,
        html: str,
        attachment: EmailAttachment,
    ) -> None: ...

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

    def send_quote(
        self,
        *,
        sender: EmailAddress,
        recipient: EmailAddress,
        subject: str,
        text: str,
        html: str,
        attachment: EmailAttachment,
    ) -> None:
        logger.warning(
            "[EMAIL DEVELOPMENT] quote from=%s to=%s subject=%s attachment=%s (%d bytes)",
            sender.formatted(), recipient.formatted(), subject, attachment.filename, len(attachment.content),
        )

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


class TransactionalEmailService:
    """Construye los mensajes comunes y delega el transporte al proveedor."""

    def _send(
        self,
        *,
        recipient: str,
        subject: str,
        text: str,
        html: str,
        sender: EmailAddress | None = None,
        reply_to: EmailAddress | None = None,
        attachments: tuple[EmailAttachment, ...] = (),
    ) -> None:
        raise NotImplementedError

    def send_quote(
        self,
        *,
        sender: EmailAddress,
        recipient: EmailAddress,
        subject: str,
        text: str,
        html: str,
        attachment: EmailAttachment,
    ) -> None:
        # Las respuestas del cliente llegan siempre al responsable (Reply-To),
        # aunque el proveedor no permita usar su dirección como remitente.
        self._send(
            recipient=recipient.formatted(), subject=subject, text=text, html=html,
            sender=sender, reply_to=sender, attachments=(attachment,),
        )

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


class SmtpEmailService(TransactionalEmailService):
    """Envía correos transaccionales mediante un servidor SMTP con STARTTLS."""

    def __init__(self) -> None:
        if not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD:
            raise RuntimeError(
                "SMTP_USERNAME and SMTP_PASSWORD are required when EMAIL_PROVIDER=smtp."
            )

    def _send(
        self,
        *,
        recipient: str,
        subject: str,
        text: str,
        html: str,
        sender: EmailAddress | None = None,
        reply_to: EmailAddress | None = None,
        attachments: tuple[EmailAttachment, ...] = (),
    ) -> None:
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = sender.formatted() if sender else formataddr(
            (settings.EMAIL_FROM_NAME, settings.EMAIL_FROM_ADDRESS)
        )
        if reply_to:
            message["Reply-To"] = reply_to.formatted()
        message["To"] = recipient
        message.set_content(text)
        message.add_alternative(html, subtype="html")
        for attachment in attachments:
            maintype, subtype = attachment.mime_type.split("/", 1)
            message.add_attachment(
                attachment.content, maintype=maintype, subtype=subtype, filename=attachment.filename,
            )
        # Sobre (MAIL FROM) con la cuenta autenticada: así el servidor SMTP no
        # rechaza el envío aunque el encabezado From sea el del responsable.
        envelope_from = settings.SMTP_USERNAME or settings.EMAIL_FROM_ADDRESS

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
            smtp.send_message(message, from_addr=envelope_from)


class ResendEmailService(TransactionalEmailService):
    """Envía correos mediante la API HTTPS de Resend."""

    def __init__(self) -> None:
        if not settings.RESEND_API_KEY:
            raise RuntimeError(
                "RESEND_API_KEY is required when EMAIL_PROVIDER=resend."
            )

    def _send(
        self,
        *,
        recipient: str,
        subject: str,
        text: str,
        html: str,
        sender: EmailAddress | None = None,
        reply_to: EmailAddress | None = None,
        attachments: tuple[EmailAttachment, ...] = (),
    ) -> None:
        # Resend solo acepta remitentes de dominios verificados: se usa la
        # dirección configurada con el nombre del responsable, y Reply-To a él.
        from_name = sender.name if sender and sender.name else settings.EMAIL_FROM_NAME
        body = {
            "from": formataddr((from_name, settings.EMAIL_FROM_ADDRESS)),
            "to": [recipient],
            "subject": subject,
            "text": text,
            "html": html,
        }
        if reply_to:
            body["reply_to"] = reply_to.formatted()
        if attachments:
            body["attachments"] = [
                {"filename": a.filename, "content": base64.b64encode(a.content).decode("ascii")}
                for a in attachments
            ]
        payload = json.dumps(body).encode("utf-8")
        request = Request(
            settings.RESEND_API_URL,
            data=payload,
            headers={
                "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                "Content-Type": "application/json",
                "User-Agent": "Flowdesk/1.0",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=20) as response:
                if response.status not in (200, 201):
                    raise RuntimeError(
                        f"Resend returned unexpected status {response.status}."
                    )
        except HTTPError as error:
            raise RuntimeError(
                f"Resend rejected the email request with status {error.code}."
            ) from error
        except URLError as error:
            raise RuntimeError("Could not connect to the Resend API.") from error

@lru_cache
def get_email_service() -> EmailService:
    provider = settings.EMAIL_PROVIDER.strip().lower()
    if provider == "development":
        return DevelopmentEmailService()
    if provider == "smtp":
        return SmtpEmailService()
    if provider == "resend":
        return ResendEmailService()
    raise RuntimeError(
        f"Unsupported EMAIL_PROVIDER '{settings.EMAIL_PROVIDER}'. "
        "Use 'development', 'smtp' or 'resend'."
    )
