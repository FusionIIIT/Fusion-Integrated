
from datetime import date

from django.test import SimpleTestCase
from rest_framework.exceptions import ValidationError

from modules.elm.api.serializers import LeaveRequestCreateSerializer


class LeaveRequestCreateSerializerTests(SimpleTestCase):
    def valid_payload(self, **overrides):
        payload = {
            "category": "CL",
            "start_date": "2026-10-27",
            "end_date": "2026-10-27",
            "half_day": "full",
            "reason": "Personal work",
            "station_leave_required": False,
            "station_leave_details": "",
            "substitute_user_id": None,
        }
        payload.update(overrides)
        return payload

    def test_valid_full_day_leave(self):
        serializer = LeaveRequestCreateSerializer(
            data=self.valid_payload()
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_end_date_before_start_date_is_rejected(self):
        serializer = LeaveRequestCreateSerializer(data=self.valid_payload(
            start_date="2026-10-28",
            end_date="2026-10-27",
        ))
        self.assertFalse(serializer.is_valid())
        self.assertIn("end_date", serializer.errors)

    def test_station_leave_requires_details(self):
        serializer = LeaveRequestCreateSerializer(data=self.valid_payload(
            station_leave_required=True,
            station_leave_details="   ",
        ))
        self.assertFalse(serializer.is_valid())
        self.assertIn("station_leave_details", serializer.errors)

    def test_nonpositive_substitute_id_is_rejected(self):
        for employee_id in (0, -1):
            with self.subTest(employee_id=employee_id):
                serializer = LeaveRequestCreateSerializer(
                    data=self.valid_payload(substitute_user_id=employee_id)
                )
                self.assertFalse(serializer.is_valid())
                self.assertIn("substitute_user_id", serializer.errors)

    def test_half_day_cannot_span_multiple_dates(self):
        serializer = LeaveRequestCreateSerializer(data=self.valid_payload(
            start_date="2026-10-27",
            end_date="2026-10-28",
            half_day="first",
        ))
        self.assertFalse(serializer.is_valid())
        self.assertIn("half_day", serializer.errors)

    def test_half_day_on_one_date_is_valid(self):
        serializer = LeaveRequestCreateSerializer(data=self.valid_payload(
            start_date="2026-10-27",
            end_date="2026-10-27",
            half_day="first",
        ))
        self.assertTrue(serializer.is_valid(), serializer.errors)
