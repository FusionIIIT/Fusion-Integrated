"""API integration tests for System Admin module endpoints."""
from datetime import date, timedelta
from unittest.mock import MagicMock, patch
from rest_framework import status
from rest_framework.test import APITestCase

from fusion_auth.client import IamSession
from modules.system_admin.models import (
    ArchivedRecord,
    BasicUser,
    PurgeRequest,
    RoleAssignment,
    RoleDefinition,
)


class SystemAdminAPITests(APITestCase):

    def setUp(self):
        # Create Super Admin session
        self.super_admin_session = IamSession(
            user_id=1,
            username="super_admin",
            display_name="Super Admin",
            kind="operator",
            modules=("system_admin",),
            permissions=frozenset([
                "system_admin.user.view",
                "system_admin.user.create",
                "system_admin.user.update",
                "system_admin.user.deactivate",
                "system_admin.user.reactivate",
                "system_admin.user.bulk_manage",
                "system_admin.role.view",
                "system_admin.role.assign",
                "system_admin.role.reassign",
                "system_admin.role.revoke",
                "system_admin.role.extend",
                "system_admin.archive.view",
                "system_admin.archive.create",
                "system_admin.archive.restore",
                "system_admin.purge.request",
                "system_admin.audit.view",
                "system_admin.audit.report",
                "system_admin.config.view",
                "system_admin.config.update",
            ]),
        )

        # Standard student user
        self.student = BasicUser.objects.create(
            institute_id="2024CS99",
            user_type="student",
            email="student99@iiitdmj.ac.in",
            first_name="Aditya",
            last_name="Verma",
            programme="B.Tech",
            batch_year=2024,
            status="active",
        )

        # Standard role definition
        self.role_placement = RoleDefinition.objects.create(
            code="placement_coordinator",
            name="Placement Coordinator",
            module_association="placement_cell",
            allowed_user_types=["student", "faculty"],
            is_singular=False,
            default_validity_days=365,
        )

        # Setup mock IAM client
        self.mock_client = MagicMock()
        self.mock_client.resolve_session.return_value = self.super_admin_session
        self.patcher = patch("fusion_auth.authentication.get_client", return_value=self.mock_client)
        self.patcher.start()

        self.client.credentials(HTTP_AUTHORIZATION="Token mock-token")

    def tearDown(self):
        self.patcher.stop()

    # 1. User Endpoints
    def test_list_and_create_users(self):
        # List users
        res = self.client.get("/api/v1/system_admin/users")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(res.json()), 1)

        # Create user
        create_res = self.client.post(
            "/api/v1/system_admin/users",
            {
                "institute_id": "2024CS88",
                "user_type": "student",
                "email": "student88@iiitdmj.ac.in",
                "first_name": "Karan",
                "last_name": "Mehta",
                "programme": "B.Tech",
                "batch_year": 2024,
            },
            format="json",
        )
        self.assertEqual(create_res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(create_res.json()["institute_id"], "2024CS88")

    def test_update_profile_and_deactivate(self):
        # Update user profile
        res = self.client.patch(
            f"/api/v1/system_admin/users/{self.student.user_id}",
            {"first_name": "Aditya Kumar"},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.json()["first_name"], "Aditya Kumar")

        # Deactivate user
        deact_res = self.client.post(
            f"/api/v1/system_admin/users/{self.student.user_id}/deactivate",
            {"reason": "Graduated alumni"},
            format="json",
        )
        self.assertEqual(deact_res.status_code, status.HTTP_200_OK)
        self.assertEqual(deact_res.json()["status"], "deactivated")

    # 2. Role Endpoints
    def test_roles_endpoints(self):
        res = self.client.get("/api/v1/system_admin/roles/definitions")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        res2 = self.client.get("/api/v1/system_admin/roles/vacancies")
        self.assertEqual(res2.status_code, status.HTTP_200_OK)

        # Assign role
        assign_res = self.client.post(
            "/api/v1/system_admin/roles/assignments",
            {
                "user_id": self.student.user_id,
                "role_code": "placement_coordinator",
                "start_date": str(date.today()),
                "end_date": str(date.today() + timedelta(days=90)),
                "reason": "Student coordinator",
            },
            format="json",
        )
        self.assertEqual(assign_res.status_code, status.HTTP_201_CREATED)

    # 3. Dashboard Endpoint
    def test_dashboard_endpoint(self):
        res = self.client.get("/api/v1/system_admin/dashboard")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()
        self.assertIn("users", data)
        self.assertIn("roles", data)
        self.assertIn("security", data)

    # 4. Config Endpoint
    def test_config_endpoint(self):
        res = self.client.get("/api/v1/system_admin/config")
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Update permitted config
        patch_res = self.client.patch(
            "/api/v1/system_admin/config",
            {"key": "password_rotation_days", "value": 45},
            format="json",
        )
        self.assertEqual(patch_res.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_res.json()["value"], 45)

    # 5. Auth Endpoint
    def test_auth_login(self):
        res = self.client.post(
            "/api/v1/system_admin/auth/login",
            {
                "username": "super_admin",
                "password": "StrongPassword123#",
                "two_factor_code": "123456",
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("session_key", res.json())
