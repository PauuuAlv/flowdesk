import unittest

from pydantic import ValidationError

from app.core.platform_permissions import (
    OPERATOR_ROLE_KEY,
    PLATFORM_PERMISSION_CATALOG,
    PLATFORM_PERMISSION_CODES,
    PLATFORM_ROLE_TEMPLATES,
    SUPERADMIN_ROLE_KEY,
    VIEWER_ROLE_KEY,
)
from app.core.permissions import PERMISSION_CODES
from app.schemas.platform_role import SavePlatformRoleRequest
from app.security.platform_admin_auth import require_platform_permission


class PlatformAccessContractTests(unittest.TestCase):
    def test_platform_catalog_codes_are_unique_and_namespaced(self):
        codes = [code for code, _module, _description in PLATFORM_PERMISSION_CATALOG]
        self.assertEqual(len(codes), len(set(codes)))
        for code, module, description in PLATFORM_PERMISSION_CATALOG:
            self.assertTrue(code.startswith(f"platform.{module}."))
            self.assertTrue(description)

    def test_platform_and_tenant_permissions_never_overlap(self):
        self.assertFalse(set(PLATFORM_PERMISSION_CODES) & set(PERMISSION_CODES))

    def test_default_platform_roles(self):
        templates = {t["key"]: t for t in PLATFORM_ROLE_TEMPLATES}
        self.assertEqual(set(templates), {SUPERADMIN_ROLE_KEY, OPERATOR_ROLE_KEY, VIEWER_ROLE_KEY})
        self.assertTrue(templates[SUPERADMIN_ROLE_KEY]["is_protected"])
        self.assertEqual(set(templates[SUPERADMIN_ROLE_KEY]["permissions"]), set(PLATFORM_PERMISSION_CODES))
        for template in PLATFORM_ROLE_TEMPLATES:
            self.assertTrue(set(template["permissions"]).issubset(PLATFORM_PERMISSION_CODES))

    def test_viewer_role_is_read_only_and_operator_cannot_manage_team(self):
        templates = {t["key"]: t for t in PLATFORM_ROLE_TEMPLATES}
        self.assertTrue(all(code.endswith(".view") for code in templates[VIEWER_ROLE_KEY]["permissions"]))
        operator = set(templates[OPERATOR_ROLE_KEY]["permissions"])
        self.assertFalse({"platform.team.invite", "platform.team.update", "platform.roles.update"} & operator)

    def test_role_request_rejects_tenant_or_unknown_permissions(self):
        with self.assertRaises(ValidationError):
            SavePlatformRoleRequest(name="Soporte", description="Atiende a las empresas.", permissions=["users.view"])

    def test_role_request_removes_duplicates(self):
        request = SavePlatformRoleRequest(
            name="Soporte",
            description="Atiende a las empresas.",
            permissions=["platform.tenants.view", "platform.tenants.view"],
        )
        self.assertEqual(request.permissions, ["platform.tenants.view"])

    def test_dependency_rejects_unknown_permission_codes(self):
        with self.assertRaises(ValueError):
            require_platform_permission("platform.unknown.view")


if __name__ == "__main__":
    unittest.main()
