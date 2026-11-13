import unittest
from datetime import datetime, timezone
from pydantic import ValidationError
from app.schemas.activity import SaveActivityRequest, UpdateActivityStatusRequest


class ActivityContractTests(unittest.TestCase):
    def test_payload_normalizes_title_and_description(self):
        value=SaveActivityRequest(client_id="client",owner_user_id="owner",activity_type="call",title="  Revisar   propuesta ",description="  Confirmar alcance  ",scheduled_at=datetime.now(timezone.utc))
        self.assertEqual(value.title,"Revisar propuesta")
        self.assertEqual(value.description,"Confirmar alcance")

    def test_activity_type_is_restricted(self):
        with self.assertRaises(ValidationError):
            SaveActivityRequest(client_id="client",owner_user_id="owner",activity_type="visit",title="Visita",scheduled_at=datetime.now(timezone.utc))

    def test_status_is_restricted(self):
        with self.assertRaises(ValidationError):
            UpdateActivityStatusRequest(status="deleted")


if __name__=="__main__": unittest.main()
