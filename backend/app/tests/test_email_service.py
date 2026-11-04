import unittest
from unittest.mock import MagicMock, patch

from app.core.config import settings
from app.services.email import (
    DevelopmentEmailService,
    SmtpEmailService,
    get_email_service,
)


class DevelopmentEmailServiceTests(unittest.TestCase):
    def setUp(self):
        self.service = DevelopmentEmailService()

    def test_invitation_is_logged_in_development(self):
        with self.assertLogs("flowdesk.email", level="WARNING") as logs:
            self.service.send_invitation(
                recipient="user@example.com",
                recipient_name="Usuario",
                invitation_url="http://localhost/accept-invite?token=test-token",
                tenant_name="Empresa de prueba",
            )
        self.assertIn("invitation", logs.output[0])
        self.assertIn("user@example.com", logs.output[0])

    def test_password_reset_is_logged_in_development(self):
        with self.assertLogs("flowdesk.email", level="WARNING") as logs:
            self.service.send_password_reset(
                recipient="user@example.com",
                recipient_name="Usuario",
                reset_url="http://localhost/reset-password?token=test-token",
            )
        self.assertIn("password_reset", logs.output[0])

    def test_factory_returns_development_service_by_default(self):
        get_email_service.cache_clear()
        self.assertIsInstance(get_email_service(), DevelopmentEmailService)


class SmtpEmailServiceTests(unittest.TestCase):
    def setUp(self):
        self.previous_values = {
            "EMAIL_PROVIDER": settings.EMAIL_PROVIDER,
            "EMAIL_FROM_ADDRESS": settings.EMAIL_FROM_ADDRESS,
            "SMTP_USERNAME": settings.SMTP_USERNAME,
            "SMTP_PASSWORD": settings.SMTP_PASSWORD,
        }
        settings.EMAIL_PROVIDER = "smtp"
        settings.EMAIL_FROM_ADDRESS = "flowdesk03@gmail.com"
        settings.SMTP_USERNAME = "flowdesk03@gmail.com"
        settings.SMTP_PASSWORD = "app-password-for-test"
        get_email_service.cache_clear()

    def tearDown(self):
        for key, value in self.previous_values.items():
            setattr(settings, key, value)
        get_email_service.cache_clear()

    def test_factory_returns_smtp_service(self):
        self.assertIsInstance(get_email_service(), SmtpEmailService)

    @patch("app.services.email.smtplib.SMTP")
    def test_invitation_uses_tls_login_and_sends_message(self, smtp_class):
        smtp = MagicMock()
        smtp_class.return_value.__enter__.return_value = smtp

        SmtpEmailService().send_invitation(
            recipient="user@example.com",
            recipient_name="Usuario",
            invitation_url="https://flowdesk.example/accept-invite?token=test",
            tenant_name="Empresa de prueba",
        )

        smtp.starttls.assert_called_once_with()
        smtp.login.assert_called_once_with(
            "flowdesk03@gmail.com", "app-password-for-test"
        )
        smtp.send_message.assert_called_once()
        message = smtp.send_message.call_args.args[0]
        self.assertEqual(message["To"], "user@example.com")
        self.assertIn("Empresa de prueba", message["Subject"])

    def test_missing_smtp_credentials_fails_fast(self):
        settings.SMTP_PASSWORD = None
        with self.assertRaisesRegex(RuntimeError, "SMTP_USERNAME and SMTP_PASSWORD"):
            SmtpEmailService()


if __name__ == "__main__":
    unittest.main()
