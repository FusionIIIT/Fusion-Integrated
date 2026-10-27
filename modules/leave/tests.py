from datetime import date
from unittest.mock import patch

from django.test import SimpleTestCase
from django.urls import reverse
from rest_framework import serializers

from modules.leave.api.serializers import LeaveRequestSerializer
from modules.leave.services import (
    create_leave_request,
    update_leave_request,
)


class LeaveRouteTests(SimpleTestCase):
    def test_withdraw_route_is_registered(self):
        self.assertEqual(
            reverse("leave-request-withdraw", kwargs={"pk": 1}),
            "/api/v1/leave/requests/1/withdraw",
        )

    def test_leave_routes_are_registered(self):
        self.assertEqual(reverse("leave-types"), "/api/v1/leave/types")
        self.assertEqual(
            reverse("leave-requests"), "/api/v1/leave/requests"
        )
        self.assertEqual(
            reverse("leave-request-detail", kwargs={"pk": 1}),
            "/api/v1/leave/requests/1",
        )


class LeaveValidationTests(SimpleTestCase):
    def test_end_date_before_start_date_is_rejected_by_service(self):
        with self.assertRaisesRegex(
            ValueError, "End date cannot be before start date"
        ):
            create_leave_request(
                user=None,
                leave_type=None,
                start_date=date(2026, 11, 10),
                end_date=date(2026, 11, 9),
            )

    def test_serializer_rejects_reversed_dates(self):
        serializer = LeaveRequestSerializer()
        with self.assertRaises(serializers.ValidationError):
            serializer.validate({
                "start_date": date(2026, 11, 10),
                "end_date": date(2026, 11, 9),
            })

    @patch("modules.leave.services.LeaveRequest.objects.get")
    def test_invalid_status_is_rejected(self, mock_get):
        mock_get.return_value = object()
        with self.assertRaisesRegex(ValueError, "Invalid status update"):
            update_leave_request(1, "cancelled")

    @patch("modules.leave.services.LeaveRequest.objects.get")
    def test_valid_status_update_saves_request(self, mock_get):
        request = mock_get.return_value
        result = update_leave_request(1, "approved")
        self.assertEqual(request.status, "approved")
        request.save.assert_called_once_with()
        self.assertIs(result, request)
