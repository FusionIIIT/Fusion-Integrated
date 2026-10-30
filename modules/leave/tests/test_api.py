"""API integration tests for leave endpoints."""
from datetime import date
from decimal import Decimal
from rest_framework import status
from rest_framework.test import APITestCase

from fusion_auth.principal import Principal
from modules.leave.domain.constants import LEAVE_CL, LEAVE_EL
from modules.leave.models import LeaveBalance, LeaveRequest
from modules.leave.services.leave import ensure_user_balances


class TestLeaveApi(APITestCase):
    def setUp(self):
        super().setUp()
        self.emp_id = 301
        self.sub_id = 302
        self.reviewer_id = 401

        # Seed balances
        ensure_user_balances(self.emp_id, kind="staff", year=2026)
        ensure_user_balances(self.sub_id, kind="staff", year=2026)

        # Mock principal for employee
        self.emp_principal = Principal(
            user_id=self.emp_id,
            username="employee1",
            display_name="Employee One",
            kind="staff",
            active_role="staff",
            roles=("staff",),
            permissions=frozenset([
                "leave.application.view_self",
                "leave.application.create",
                "leave.substitute.respond",
            ]),
            modules=("leave",),
        )

        # Mock principal for reviewer
        self.reviewer_principal = Principal(
            user_id=self.reviewer_id,
            username="hod_reviewer",
            display_name="Head of Dept",
            kind="faculty",
            active_role="HOD",
            roles=("faculty", "HOD"),
            permissions=frozenset([
                "leave.application.view_self",
                "leave.application.create",
                "leave.application.review",
                "leave.substitute.respond",
            ]),
            modules=("leave",),
        )

    def test_get_balances(self):
        """GET /api/v1/leave/balances/ returns the caller's balances."""
        self.client.force_authenticate(user=self.emp_principal)
        response = self.client.get("/api/v1/leave/balances/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        categories = [item["category"] for item in response.data]
        self.assertIn("CL", categories)
        self.assertIn("EL", categories)

    def test_apply_and_view_applications(self):
        """POST & GET /api/v1/leave/applications/."""
        self.client.force_authenticate(user=self.emp_principal)
        payload = {
            "category": "CL",
            "start_date": "2026-11-02",
            "end_date": "2026-11-02",
            "half_day": "first_half",
            "purpose": "Personal errands",
        }
        res = self.client.post("/api/v1/leave/applications/", payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["category"], "CL")
        self.assertEqual(res.data["requested_days"], "0.5")

        # GET applications
        get_res = self.client.get("/api/v1/leave/applications/")
        self.assertEqual(get_res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(get_res.data), 1)

    def test_substitute_and_review_queues(self):
        """Test substitute response and reviewer approval flow via API."""
        self.client.force_authenticate(user=self.emp_principal)
        payload = {
            "category": "CL",
            "start_date": "2026-11-09",
            "end_date": "2026-11-10",
            "purpose": "Conference",
            "substitute_user_id": self.sub_id,
        }
        create_res = self.client.post("/api/v1/leave/applications/", payload, format="json")
        req_id = create_res.data["id"]

        # Substitute authenticates and views substitute queue
        sub_principal = Principal(
            user_id=self.sub_id,
            username="sub1",
            display_name="Substitute One",
            kind="staff",
            active_role="staff",
            roles=("staff",),
            permissions=frozenset(["leave.substitute.respond"]),
            modules=("leave",),
        )
        self.client.force_authenticate(user=sub_principal)
        sub_queue = self.client.get("/api/v1/leave/substitute-queue/")
        self.assertEqual(sub_queue.status_code, status.HTTP_200_OK)
        self.assertEqual(len(sub_queue.data), 1)

        # Substitute accepts
        resp_res = self.client.post(
            f"/api/v1/leave/substitute-queue/{req_id}/respond/",
            {"accept": True, "remarks": "Confirmed"},
            format="json",
        )
        self.assertEqual(resp_res.status_code, status.HTTP_200_OK)

        # Reviewer views approvals queue and approves
        self.client.force_authenticate(user=self.reviewer_principal)
        appr_queue = self.client.get("/api/v1/leave/approvals-queue/")
        self.assertEqual(appr_queue.status_code, status.HTTP_200_OK)
        self.assertEqual(len(appr_queue.data), 1)

        decide_res = self.client.post(
            f"/api/v1/leave/approvals-queue/{req_id}/decide/",
            {"decision": "approved", "remarks": "Approved by HOD"},
            format="json",
        )
        self.assertEqual(decide_res.status_code, status.HTTP_200_OK)
        self.assertEqual(decide_res.data["status"], "approved")
