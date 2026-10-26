"""Tests for ELM HTTP API views and DRF permission enforcement."""
from __future__ import annotations

import unittest
from datetime import date
from unittest.mock import MagicMock, patch

from rest_framework import status
from rest_framework.test import APIRequestFactory, force_authenticate

from fusion_auth.principal import Principal
from modules.leave.api import views as v
from modules.leave.models import LeaveApplication


def _actor(user_id: int = 101, permissions: tuple[str, ...] = (), modules: tuple[str, ...] = ("leave",)) -> Principal:
    return Principal(
        user_id=user_id,
        username=f"user_{user_id}",
        display_name=f"User {user_id}",
        kind="employee",
        active_role="Employee",
        roles=("Employee",),
        permissions=frozenset(permissions),
        modules=modules,
    )


def _auth_request(request, actor: Principal):
    request.principal = actor
    force_authenticate(request, user=actor)


class TestLeaveApiViews(unittest.TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

    def test_apply_without_module_grant_returns_403(self):
        actor = _actor(101, permissions=("leave.application.create",), modules=())  # No "leave" module grant
        request = self.factory.post("/api/v1/leave/applications", {}, format="json")
        _auth_request(request, actor)
        response = v.LeaveApplicationListCreateView.as_view()(request)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_apply_without_create_permission_returns_403(self):
        actor = _actor(101, permissions=(), modules=("leave",))  # No create permission
        request = self.factory.post("/api/v1/leave/applications", {}, format="json")
        _auth_request(request, actor)
        response = v.LeaveApplicationListCreateView.as_view()(request)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch("modules.leave.services.applications.apply_leave")
    def test_apply_with_valid_data_returns_201(self, mock_apply):
        actor = _actor(101, permissions=("leave.application.create",), modules=("leave",))
        dummy_app = MagicMock(spec=LeaveApplication)
        dummy_app.id = 1
        dummy_app.user_id = 101
        dummy_app.category = "CL"
        dummy_app.start_date = date(2026, 11, 2)
        dummy_app.end_date = date(2026, 11, 3)
        dummy_app.reason = "Personal"
        dummy_app.half_day_cl = False
        dummy_app.substitute_id = None
        dummy_app.station_leave_details = {}
        dummy_app.status = "submitted"
        dummy_app.posting_id = 0
        dummy_app.created_at = None
        dummy_app.updated_at = None
        dummy_app.chargeable_days.return_value = 2.0
        mock_apply.return_value = dummy_app

        payload = {
            "category": "CL",
            "start_date": "2026-11-02",
            "end_date": "2026-11-03",
            "reason": "Personal",
        }
        request = self.factory.post("/api/v1/leave/applications", payload, format="json")
        _auth_request(request, actor)
        response = v.LeaveApplicationListCreateView.as_view()(request)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "submitted")

    def test_apply_with_invalid_choice_returns_400(self):
        actor = _actor(101, permissions=("leave.application.create",), modules=("leave",))
        payload = {
            "category": "INVALID_CAT",
            "start_date": "2026-11-02",
            "end_date": "2026-11-03",
        }
        request = self.factory.post("/api/v1/leave/applications", payload, format="json")
        _auth_request(request, actor)
        response = v.LeaveApplicationListCreateView.as_view()(request)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_substitute_response_without_permission_returns_403(self):
        actor = _actor(102, permissions=(), modules=("leave",))
        request = self.factory.post("/api/v1/leave/applications/1/substitute", {"action": "accept"}, format="json")
        _auth_request(request, actor)
        response = v.SubstituteResponseView.as_view()(request, pk=1)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch("modules.leave.services.applications.respond_substitute")
    def test_substitute_response_success(self, mock_respond):
        actor = _actor(102, permissions=("leave.substitute.respond",), modules=("leave",))
        dummy_app = MagicMock(spec=LeaveApplication)
        dummy_app.id = 1
        dummy_app.user_id = 101
        dummy_app.category = "CL"
        dummy_app.start_date = date(2026, 11, 2)
        dummy_app.end_date = date(2026, 11, 3)
        dummy_app.reason = ""
        dummy_app.half_day_cl = False
        dummy_app.substitute_id = 102
        dummy_app.station_leave_details = {}
        dummy_app.status = "under_review"
        dummy_app.posting_id = 0
        dummy_app.created_at = None
        dummy_app.updated_at = None
        dummy_app.chargeable_days.return_value = 2.0
        mock_respond.return_value = dummy_app

        request = self.factory.post(
            "/api/v1/leave/applications/1/substitute",
            {"action": "accept", "reason": "Will handle"},
            format="json",
        )
        _auth_request(request, actor)
        response = v.SubstituteResponseView.as_view()(request, pk=1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "under_review")

    def test_review_without_permission_returns_403(self):
        actor = _actor(201, permissions=(), modules=("leave",))
        request = self.factory.post("/api/v1/leave/applications/1/review", {"action": "recommend"}, format="json")
        _auth_request(request, actor)
        response = v.ReviewApplicationView.as_view()(request, pk=1)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_sanction_without_permission_returns_403(self):
        actor = _actor(301, permissions=(), modules=("leave",))
        request = self.factory.post("/api/v1/leave/applications/1/sanction", {"action": "approve"}, format="json")
        _auth_request(request, actor)
        response = v.SanctionApplicationView.as_view()(request, pk=1)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_withdraw_without_permission_returns_403(self):
        actor = _actor(101, permissions=(), modules=("leave",))
        request = self.factory.post("/api/v1/leave/applications/1/withdraw", {}, format="json")
        _auth_request(request, actor)
        response = v.WithdrawApplicationView.as_view()(request, pk=1)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @patch("modules.leave.services.applications.review_application")
    def test_review_success(self, mock_review):
        actor = _actor(201, permissions=("leave.application.review",), modules=("leave",))
        dummy_app = MagicMock(spec=LeaveApplication)
        dummy_app.id = 1
        dummy_app.user_id = 101
        dummy_app.category = "CL"
        dummy_app.start_date = date(2026, 11, 2)
        dummy_app.end_date = date(2026, 11, 3)
        dummy_app.reason = ""
        dummy_app.half_day_cl = False
        dummy_app.substitute_id = None
        dummy_app.station_leave_details = {}
        dummy_app.status = "awaiting_sanction"
        dummy_app.posting_id = 0
        dummy_app.created_at = None
        dummy_app.updated_at = None
        dummy_app.chargeable_days.return_value = 2.0
        mock_review.return_value = dummy_app

        request = self.factory.post(
            "/api/v1/leave/applications/1/review",
            {"action": "recommend", "reason": "Looks good"},
            format="json",
        )
        _auth_request(request, actor)
        response = v.ReviewApplicationView.as_view()(request, pk=1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "awaiting_sanction")

    @patch("modules.leave.services.applications.sanction_application")
    def test_sanction_success(self, mock_sanction):
        actor = _actor(301, permissions=("leave.application.approve",), modules=("leave",))
        dummy_app = MagicMock(spec=LeaveApplication)
        dummy_app.id = 1
        dummy_app.user_id = 101
        dummy_app.category = "CL"
        dummy_app.start_date = date(2026, 11, 2)
        dummy_app.end_date = date(2026, 11, 3)
        dummy_app.reason = ""
        dummy_app.half_day_cl = False
        dummy_app.substitute_id = None
        dummy_app.station_leave_details = {}
        dummy_app.status = "approved"
        dummy_app.posting_id = 0
        dummy_app.created_at = None
        dummy_app.updated_at = None
        dummy_app.chargeable_days.return_value = 2.0
        mock_sanction.return_value = dummy_app

        request = self.factory.post(
            "/api/v1/leave/applications/1/sanction",
            {"action": "approve"},
            format="json",
        )
        _auth_request(request, actor)
        response = v.SanctionApplicationView.as_view()(request, pk=1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "approved")

    @patch("modules.leave.services.applications.withdraw_application")
    def test_withdraw_success(self, mock_withdraw):
        actor = _actor(101, permissions=("leave.application.delete",), modules=("leave",))
        dummy_app = MagicMock(spec=LeaveApplication)
        dummy_app.id = 1
        dummy_app.user_id = 101
        dummy_app.category = "CL"
        dummy_app.start_date = date(2099, 11, 2)
        dummy_app.end_date = date(2099, 11, 3)
        dummy_app.reason = ""
        dummy_app.half_day_cl = False
        dummy_app.substitute_id = None
        dummy_app.station_leave_details = {}
        dummy_app.status = "withdrawn"
        dummy_app.posting_id = 0
        dummy_app.created_at = None
        dummy_app.updated_at = None
        dummy_app.chargeable_days.return_value = 2.0
        mock_withdraw.return_value = dummy_app

        request = self.factory.post("/api/v1/leave/applications/1/withdraw", {"reason": "Change"}, format="json")
        _auth_request(request, actor)
        response = v.WithdrawApplicationView.as_view()(request, pk=1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "withdrawn")

    @patch("modules.leave.selectors.scoping.applications_for")
    def test_detail_view_success(self, mock_scoping):
        actor = _actor(101, permissions=("leave.application.view",), modules=("leave",))
        dummy_app = MagicMock(spec=LeaveApplication)
        dummy_app.id = 1
        dummy_app.user_id = 101
        dummy_app.category = "CL"
        dummy_app.start_date = date(2026, 11, 2)
        dummy_app.end_date = date(2026, 11, 3)
        dummy_app.reason = ""
        dummy_app.half_day_cl = False
        dummy_app.substitute_id = None
        dummy_app.station_leave_details = {}
        dummy_app.status = "submitted"
        dummy_app.posting_id = 0
        dummy_app.created_at = None
        dummy_app.updated_at = None
        dummy_app.chargeable_days.return_value = 2.0

        mock_qs = MagicMock()
        mock_qs.get.return_value = dummy_app
        mock_scoping.return_value = mock_qs

        request = self.factory.get("/api/v1/leave/applications/1")
        _auth_request(request, actor)
        response = v.LeaveApplicationDetailView.as_view()(request, pk=1)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], 1)

    @patch("modules.leave.selectors.scoping.applications_for")
    def test_detail_view_not_found_returns_404(self, mock_scoping):
        actor = _actor(101, permissions=("leave.application.view",), modules=("leave",))
        mock_qs = MagicMock()
        mock_qs.model.DoesNotExist = Exception
        mock_qs.get.side_effect = mock_qs.model.DoesNotExist
        mock_scoping.return_value = mock_qs

        request = self.factory.get("/api/v1/leave/applications/999")
        _auth_request(request, actor)
        response = v.LeaveApplicationDetailView.as_view()(request, pk=999)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch("modules.leave.selectors.scoping.balances_for")
    def test_balance_list_view_success(self, mock_balances):
        actor = _actor(101, permissions=("leave.application.view",), modules=("leave",))
        mock_qs = MagicMock()
        mock_qs.order_by.return_value = []
        mock_balances.return_value = mock_qs

        request = self.factory.get("/api/v1/leave/balances")
        _auth_request(request, actor)
        response = v.LeaveBalanceListView.as_view()(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])


if __name__ == "__main__":
    unittest.main()
