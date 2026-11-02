import unittest

from app.services.email import DevelopmentEmailService, get_email_service


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


if __name__ == "__main__":
    unittest.main()
