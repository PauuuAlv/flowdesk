import unittest

from pydantic import ValidationError

from app.core.permissions import (
    ADMIN_ROLE_KEY,
    MEMBER_ROLE_KEY,
    PERMISSION_CATALOG,
    PERMISSION_CODES,
    ROLE_TEMPLATES,
    VIEWER_ROLE_KEY,
)
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

    def test_default_roles_are_admin_member_viewer(self):
        templates = {t["key"]: t for t in ROLE_TEMPLATES}
        self.assertEqual(set(templates), {ADMIN_ROLE_KEY, MEMBER_ROLE_KEY, VIEWER_ROLE_KEY})
        self.assertEqual(templates[VIEWER_ROLE_KEY]["name"], "Visor")
        self.assertEqual(templates[MEMBER_ROLE_KEY]["name"], "Miembro")

    def test_admin_template_has_every_permission_and_is_protected(self):
        admin = next(t for t in ROLE_TEMPLATES if t["key"] == ADMIN_ROLE_KEY)
        self.assertTrue(admin["is_protected"])
        self.assertEqual(set(admin["permissions"]), set(PERMISSION_CODES))

    def test_viewer_template_is_read_only(self):
        viewer = next(t for t in ROLE_TEMPLATES if t["key"] == VIEWER_ROLE_KEY)
        self.assertTrue(viewer["permissions"])
        self.assertTrue(all(code.endswith(".view") for code in viewer["permissions"]))

    def test_permission_catalog_codes_are_unique_and_namespaced(self):
        codes = [code for code, _module, _description in PERMISSION_CATALOG]
        self.assertEqual(len(codes), len(set(codes)))
        for code, module, description in PERMISSION_CATALOG:
            self.assertTrue(code.startswith(f"{module}."))
            self.assertTrue(description)

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
