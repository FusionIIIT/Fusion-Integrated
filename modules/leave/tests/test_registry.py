import unittest

from modules.leave.registry import (
    MODULE,
    PERMISSIONS,
    ROLE_GRANTS,
    SYSTEM_PERMISSIONS,
)


class TestLeaveRegistry(unittest.TestCase):

    def test_module_metadata(self):
        self.assertEqual(MODULE["code"], "leave_management")
        self.assertEqual(MODULE["status"], "active")

    def test_all_permissions_have_description(self):
        for code, description in PERMISSIONS:
            self.assertIsInstance(code, str)
            self.assertIsInstance(description, str)
            self.assertTrue(code)
            self.assertTrue(description)

    def test_every_user_permission_is_granted(self):
        all_permissions = {code for code, _ in PERMISSIONS}
        user_permissions = all_permissions - set(SYSTEM_PERMISSIONS)
        granted_permissions = set()

        for roles in ROLE_GRANTS.values():
            granted_permissions.update(roles)

        missing_permissions = user_permissions - granted_permissions
        self.assertEqual(missing_permissions, set(), f"The following user permissions are not granted to any role: {missing_permissions}")

    def test_all_role_grants_are_declared(self):
        declared_permissions = {code for code, _ in PERMISSIONS}

        for roles in ROLE_GRANTS.values():
            for code in roles:
                self.assertIn(code, declared_permissions, f"Role grants contain undeclared permission: {code}")

    def test_system_permissions_not_granted_to_roles(self):
        for roles in ROLE_GRANTS.values():
            for code in roles:
                self.assertNotIn(code, SYSTEM_PERMISSIONS, f"System permission {code} should not be granted to any role.")

if __name__ == '__main__':
    unittest.main()
