import unittest

from pydantic import ValidationError

from app.main import app
from app.models.contact import Contact
from app.schemas.contact import CreateContactRequest, UpdateContactRequest


class ContactContractTests(unittest.TestCase):
    def test_payload_normalizes_text_and_email(self):
        payload = CreateContactRequest(
            full_name="  Paulina   Alvarado ",
            job_title="  Gerente   de Compras ",
            email="  COMPRAS@EXAMPLE.COM ",
            phone="  +52 771 123 4567 ",
        )
        self.assertEqual(payload.full_name, "Paulina Alvarado")
        self.assertEqual(payload.job_title, "Gerente de Compras")
        self.assertEqual(str(payload.email), "compras@example.com")
        self.assertEqual(payload.phone, "+52 771 123 4567")
        self.assertFalse(payload.is_primary)

    def test_optional_fields_accept_blank_values(self):
        payload = CreateContactRequest(full_name="Ana López", job_title="  ", email="", phone="")
        self.assertIsNone(payload.job_title)
        self.assertIsNone(payload.email)
        self.assertIsNone(payload.phone)

    def test_rejects_invalid_values(self):
        with self.assertRaises(ValidationError):
            CreateContactRequest(full_name="A")
        with self.assertRaises(ValidationError):
            CreateContactRequest(full_name="Ana López", email="correo-invalido")
        with self.assertRaises(ValidationError):
            UpdateContactRequest(full_name="Ana López", phone="abc")

    def test_payload_never_accepts_tenant_or_client_from_body(self):
        fields = CreateContactRequest.model_fields
        self.assertNotIn("tenant_id", fields)
        self.assertNotIn("client_id", fields)

    def test_model_is_tenant_scoped_with_single_primary_index(self):
        columns = Contact.__table__.columns
        self.assertIn("tenant_id", columns)
        self.assertFalse(columns["tenant_id"].nullable)
        primary_index = next(
            index for index in Contact.__table__.indexes if index.name == "uq_contacts_primary_per_client"
        )
        self.assertTrue(primary_index.unique)

    def test_routes_are_nested_under_clients(self):
        paths = {route.path for route in app.routes}
        self.assertIn("/api/clients/{client_id}/contacts", paths)
        self.assertIn("/api/clients/{client_id}/contacts/{contact_id}", paths)
        self.assertIn("/api/clients/{client_id}/contacts/{contact_id}/primary", paths)


if __name__ == "__main__":
    unittest.main()
