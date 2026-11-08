import unittest

from pydantic import ValidationError

from app.schemas.client import CreateClientRequest, UpdateClientStatusRequest


class ClientContractTests(unittest.TestCase):
    def test_client_payload_normalizes_text_and_email(self):
        payload = CreateClientRequest(
            company_name="  Comercializadora   del Norte ",
            contact_name="  Paulina   Alvarado ",
            email="CLIENTE@EXAMPLE.COM",
            phone="  +52 771 123 4567  ",
            notes="  Seguimiento inicial  ",
        )
        self.assertEqual(payload.company_name, "Comercializadora del Norte")
        self.assertEqual(payload.contact_name, "Paulina Alvarado")
        self.assertEqual(str(payload.email), "cliente@example.com")
        self.assertEqual(payload.phone, "+52 771 123 4567")

    def test_client_payload_rejects_invalid_email(self):
        with self.assertRaises(ValidationError):
            CreateClientRequest(
                company_name="Empresa",
                contact_name="Contacto",
                email="correo-invalido",
            )

    def test_status_rejects_unknown_values(self):
        with self.assertRaises(ValidationError):
            UpdateClientStatusRequest(status="deleted")


if __name__ == "__main__":
    unittest.main()
