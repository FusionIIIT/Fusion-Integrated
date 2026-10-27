"""API and integration unit tests for ELM endpoints.

Tests request submission, transition authorization, validation, station leave,
substitute consent gates, balance debit/restoration, and non-overlap constraints.
"""

from datetime import date, timedelta
import os
import unittest
from unittest.mock import MagicMock, patch

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.test")
import django
django.setup()

from rest_framework.test import APIRequestFactory
from rest_framework import status

from fusion_auth.principal import Principal
from modules.elm.domain.state_machine import Status
from modules.elm.registry import PERMISSIONS
from modules.elm.api.views import (
    LeaveTypeListView,
    LeaveRequestListView,
    LeaveRequestTransitionView,
    LeaveBalanceListView,
    SubstituteResponseListView,
    SubstituteResponseRespondView,
)

ELM_ALL_PERMISSIONS = frozenset([p[0] for p in PERMISSIONS] + [
    "elm.leave_request.create",
    "elm.leave_request.update",
    "elm.leave_request.approve",
])


def make_test_principal(user_id=101, permissions=None, modules=("leave_elm",)):
    perms = ELM_ALL_PERMISSIONS if permissions is None else frozenset(permissions)
    return Principal(
        user_id=user_id,
        username=f"user_{user_id}",
        display_name=f"User {user_id}",
        kind="faculty",
        active_role="faculty",
        roles=("faculty",),
        permissions=perms,
        modules=tuple(modules),
    )


class TestElmApiEndpoints(unittest.TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.principal = make_test_principal(user_id=101)

    def _mock_auth(self, req, principal=None):
        p = principal or self.principal
        req.principal = p
        return (p, "token")

    def test_anonymous_principal_refused(self):
        request = self.factory.get("/api/v1/elm/requests")
        view = LeaveRequestListView.as_view()
        response = view(request)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_missing_module_grant_refused(self):
        request = self.factory.get("/api/v1/elm/requests", HTTP_AUTHORIZATION="Token abc")
        view = LeaveRequestListView.as_view()
        unauthorized = make_test_principal(modules=())

        with patch("fusion_auth.authentication.IamSessionAuthentication.authenticate", lambda s, r: self._mock_auth(r, unauthorized)):
            response = view(request)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_leave_types_list_authenticated(self):
        request = self.factory.get("/api/v1/elm/types", HTTP_AUTHORIZATION="Token abc")
        view = LeaveTypeListView.as_view()

        with patch("fusion_auth.authentication.IamSessionAuthentication.authenticate", lambda s, r: self._mock_auth(r)), \
             patch("modules.elm.models.LeaveType.objects.filter") as mock_filter:
            mock_filter.return_value.values.return_value = [
                {"id": 1, "code": "CL", "name": "Casual Leave", "description": "8 days"}
            ]
            response = view(request)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(len(response.data), 1)
            self.assertEqual(response.data[0]["code"], "CL")

    def test_transition_invalid_status_value(self):
        request = self.factory.post(
            "/api/v1/elm/requests/1/transition",
            {"target_status": "BOGUS_STATUS"},
            format="json",
            HTTP_AUTHORIZATION="Token abc",
        )
        view = LeaveRequestTransitionView.as_view()

        with patch("fusion_auth.authentication.IamSessionAuthentication.authenticate", lambda s, r: self._mock_auth(r)), \
             patch("modules.elm.models.LeaveRequest.objects.select_related") as mock_sr:
            mock_req = MagicMock()
            mock_req.status = Status.DRAFT.value
            mock_sr.return_value.get.return_value = mock_req
            response = view(request, pk=1)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_transition_valid_status_approved(self):
        request = self.factory.post(
            "/api/v1/elm/requests/1/transition",
            {"target_status": Status.PENDING_UNIT_HEAD.value},
            format="json",
            HTTP_AUTHORIZATION="Token abc",
        )
        view = LeaveRequestTransitionView.as_view()

        with patch("fusion_auth.authentication.IamSessionAuthentication.authenticate", lambda s, r: self._mock_auth(r)), \
             patch("modules.elm.models.LeaveRequest.objects.select_related") as mock_sr, \
             patch("django.db.transaction.atomic"), \
             patch("modules.elm.models.LeaveRequestTransition.objects.create") as mock_trans_create:
            mock_req = MagicMock()
            mock_req.id = 1
            mock_req.status = Status.DRAFT.value
            mock_sr.return_value.get.return_value = mock_req

            response = view(request, pk=1)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(mock_req.status, Status.PENDING_UNIT_HEAD.value)
            mock_req.save.assert_called_once_with(update_fields=["status"])
            mock_trans_create.assert_called_once()

    def test_leave_request_submission_with_station_leave(self):
        # BR-EL-013: Station leave details captured in application
        payload = {
            "leave_type_id": 1,
            "start_date": "2026-11-01",
            "end_date": "2026-11-03",
            "reason": "Conference in Delhi",
            "is_station_leave": True,
            "station_leave_address": "IIT Delhi Campus",
            "station_leave_contact": "9876543210",
        }
        request = self.factory.post("/api/v1/elm/requests", payload, format="json", HTTP_AUTHORIZATION="Token abc")
        view = LeaveRequestListView.as_view()

        with patch("fusion_auth.authentication.IamSessionAuthentication.authenticate", lambda s, r: self._mock_auth(r)), \
             patch("modules.elm.models.LeaveRequest.objects.filter") as mock_filter, \
             patch("django.db.transaction.atomic"), \
             patch("modules.elm.models.LeaveRequest.objects.create") as mock_create, \
             patch("modules.elm.models.LeaveRequestTransition.objects.create"):
            mock_filter.return_value.exclude.return_value = []
            mock_created_req = MagicMock(id=42, status=Status.PENDING_UNIT_HEAD.value)
            mock_create.return_value = mock_created_req

            response = view(request)
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            mock_create.assert_called_once()
            kwargs = mock_create.call_args[1]
            self.assertTrue(kwargs["is_station_leave"])
            self.assertEqual(kwargs["station_leave_address"], "IIT Delhi Campus")
            self.assertEqual(kwargs["station_leave_contact"], "9876543210")

    def test_substitute_cannot_be_applicant(self):
        # BR-EL-014: Nominated substitute cannot be the applicant
        payload = {
            "leave_type_id": 1,
            "start_date": "2026-11-01",
            "end_date": "2026-11-03",
            "substitute_user_id": 101,  # Same as applicant
        }
        request = self.factory.post("/api/v1/elm/requests", payload, format="json", HTTP_AUTHORIZATION="Token abc")
        view = LeaveRequestListView.as_view()

        with patch("fusion_auth.authentication.IamSessionAuthentication.authenticate", lambda s, r: self._mock_auth(r)), \
             patch("modules.elm.models.LeaveRequest.objects.filter") as mock_filter:
            mock_filter.return_value.exclude.return_value = []
            response = view(request)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("Substitute cannot be the applicant", response.data["detail"])

    def test_applicant_non_overlap_validation(self):
        # BR-EL-012: Reject request that impermissibly overlaps active leave
        payload = {
            "leave_type_id": 1,
            "start_date": "2026-11-02",
            "end_date": "2026-11-04",
        }
        request = self.factory.post("/api/v1/elm/requests", payload, format="json", HTTP_AUTHORIZATION="Token abc")
        view = LeaveRequestListView.as_view()

        with patch("fusion_auth.authentication.IamSessionAuthentication.authenticate", lambda s, r: self._mock_auth(r)), \
             patch("modules.elm.models.LeaveRequest.objects.filter") as mock_filter:
            existing = MagicMock(
                start_date=date(2026, 11, 1),
                end_date=date(2026, 11, 3),
                half_day_type="FULL",
                leave_type=MagicMock(code="CL"),
            )
            mock_filter.return_value.exclude.return_value = [existing]
            response = view(request)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("already overlaps", response.data["detail"])

    def test_substitute_response_accept_pipeline(self):
        # CW-EL-01, BR-EL-015: Substitute accepting moves request to PENDING_UNIT_HEAD
        request = self.factory.post(
            "/api/v1/elm/substitute-responses/1/respond",
            {"status": "ACCEPTED", "remarks": "Covering lab duties"},
            format="json",
            HTTP_AUTHORIZATION="Token abc",
        )
        view = SubstituteResponseRespondView.as_view()

        with patch("fusion_auth.authentication.IamSessionAuthentication.authenticate", lambda s, r: self._mock_auth(r)), \
             patch("modules.elm.models.SubstituteResponse.objects.select_related") as mock_sr, \
             patch("modules.elm.models.SubstituteResponse.objects.filter") as mock_sub_filter, \
             patch("django.db.transaction.atomic"), \
             patch("modules.elm.models.LeaveRequestTransition.objects.create"):
            sub_mock = MagicMock(
                id=1,
                substitute_user_id=101,
                status="PENDING",
                leave_request=MagicMock(status=Status.AWAITING_SUBSTITUTE_RESPONSE.value),
            )
            mock_sr.return_value.get.return_value = sub_mock
            mock_sub_filter.return_value.count.return_value = 0  # no more pending substitutes

            response = view(request, pk=1)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(sub_mock.leave_request.status, Status.PENDING_UNIT_HEAD.value)

    def test_substitute_response_decline_pipeline(self):
        # CW-EL-01, BR-EL-015: Substitute declining transitions to APPLICANT_ACTION_REQUIRED
        request = self.factory.post(
            "/api/v1/elm/substitute-responses/1/respond",
            {"status": "DECLINED", "remarks": "Travelling on these dates"},
            format="json",
            HTTP_AUTHORIZATION="Token abc",
        )
        view = SubstituteResponseRespondView.as_view()

        with patch("fusion_auth.authentication.IamSessionAuthentication.authenticate", lambda s, r: self._mock_auth(r)), \
             patch("modules.elm.models.SubstituteResponse.objects.select_related") as mock_sr, \
             patch("django.db.transaction.atomic"), \
             patch("modules.elm.models.LeaveRequestTransition.objects.create"):
            sub_mock = MagicMock(
                id=1,
                substitute_user_id=101,
                status="PENDING",
                leave_request=MagicMock(status=Status.AWAITING_SUBSTITUTE_RESPONSE.value),
            )
            mock_sr.return_value.get.return_value = sub_mock

            response = view(request, pk=1)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(sub_mock.leave_request.status, Status.APPLICANT_ACTION_REQUIRED.value)

    def test_cancellation_rejected_after_leave_start(self):
        # BR-EL-023: Cancellation may only be requested before start date
        request = self.factory.post(
            "/api/v1/elm/requests/1/transition",
            {"target_status": Status.CANCELLATION_PENDING_UNIT_HEAD.value},
            format="json",
            HTTP_AUTHORIZATION="Token abc",
        )
        view = LeaveRequestTransitionView.as_view()

        with patch("fusion_auth.authentication.IamSessionAuthentication.authenticate", lambda s, r: self._mock_auth(r)), \
             patch("modules.elm.models.LeaveRequest.objects.select_related") as mock_sr:
            # Leave started yesterday
            mock_req = MagicMock(
                id=1,
                employee_user_id=101,
                status=Status.APPROVED.value,
                start_date=date.today() - timedelta(days=1),
            )
            mock_sr.return_value.get.return_value = mock_req

            response = view(request, pk=1)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertIn("only before its start date", response.data["detail"])

    def test_leave_approval_debits_balance(self):
        # BR-EL-010, BR-EL-023: Final approval debits the leave balance
        request = self.factory.post(
            "/api/v1/elm/requests/1/transition",
            {"target_status": Status.APPROVED.value},
            format="json",
            HTTP_AUTHORIZATION="Token abc",
        )
        view = LeaveRequestTransitionView.as_view()

        with patch("fusion_auth.authentication.IamSessionAuthentication.authenticate", lambda s, r: self._mock_auth(r)), \
             patch("modules.elm.models.LeaveRequest.objects.select_related") as mock_sr, \
             patch("django.db.transaction.atomic"), \
             patch("modules.elm.api.views.debit_leave_balance") as mock_debit, \
             patch("modules.elm.models.LeaveRequestTransition.objects.create"):
            mock_req = MagicMock(
                id=1,
                employee_user_id=101,
                status=Status.PENDING_FINAL_SANCTION.value,
                start_date=date(2026, 11, 1),
                end_date=date(2026, 11, 2),
                half_day_type="FULL",
                leave_type=MagicMock(code="EL"),
            )
            mock_sr.return_value.get.return_value = mock_req

            response = view(request, pk=1)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(mock_req.status, Status.APPROVED.value)
            mock_debit.assert_called_once()

    def test_cancellation_approval_restores_balance(self):
        # BR-EL-023: Approved cancellation restores debited balance
        request = self.factory.post(
            "/api/v1/elm/requests/1/transition",
            {"target_status": Status.CANCELLED.value},
            format="json",
            HTTP_AUTHORIZATION="Token abc",
        )
        view = LeaveRequestTransitionView.as_view()

        with patch("fusion_auth.authentication.IamSessionAuthentication.authenticate", lambda s, r: self._mock_auth(r)), \
             patch("modules.elm.models.LeaveRequest.objects.select_related") as mock_sr, \
             patch("django.db.transaction.atomic"), \
             patch("modules.elm.api.views.restore_leave_balance") as mock_restore, \
             patch("modules.elm.models.LeaveRequestTransition.objects.create"):
            mock_req = MagicMock(
                id=1,
                employee_user_id=101,
                status=Status.CANCELLATION_PENDING_UNIT_HEAD.value,
                start_date=date(2026, 11, 1),
                end_date=date(2026, 11, 2),
                half_day_type="FULL",
                leave_type=MagicMock(code="CL"),
            )
            mock_sr.return_value.get.return_value = mock_req

            response = view(request, pk=1)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(mock_req.status, Status.CANCELLED.value)
            mock_restore.assert_called_once()


if __name__ == "__main__":
    unittest.main()
