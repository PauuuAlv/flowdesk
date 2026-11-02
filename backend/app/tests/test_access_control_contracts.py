import unittest

from pydantic import ValidationError

from app.core.permissions import PERMISSION_CODES, ROLE_TEMPLATES
from app.schemas.access_control import SaveRoleRequest


class AccessControlContractTests(unittest.TestCase):
    def test_default_role_templates_are_unique(self):
        keys = [template["key"] for template in ROLE_TEMPLATES]
        names = [template["name"].lower() for template in ROLE_TEMPLATES]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(len(names), len(set(names)))

    def test_template_permissions_are_supported(self):
        supported = set(PERMISSION_CODES)
        for template in ROLE_TEMPLATES:
            self.assertTrue(set(template["permissions"]).issubset(supported))

    def test_role_request_rejects_unknown_permissions(self):
        with self.assertRaises(ValidationError):
            SaveRoleRequest(
                name="Contabilidad",
                description="Consulta información financiera.",
                permissions=["unknown.permission"],
            )

    def test_role_request_removes_duplicate_permissions(self):
        request = SaveRoleRequest(
            name="Contabilidad",
            description="Consulta información financiera.",
            permissions=["dashboard.view", "dashboard.view"],
        )
        self.assertEqual(request.permissions, ["dashboard.view"])


if __name__ == "__main__":
    unittest.main()
