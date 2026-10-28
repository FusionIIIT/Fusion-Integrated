from datetime import date

from django.test import SimpleTestCase
from rest_framework.exceptions import ValidationError

from modules.elm.api.serializers import LeaveApplicationSerializer
from modules.elm.models import LeaveType


class LeaveApplicationSerializerTests(SimpleTestCase):
    def payload(self, **overrides):
        data = {
            "employee_id": 42,
            "leave_category": LeaveType.COMPENSATION,
            "start_date": date(2026, 11, 2),
            "end_date": date(2026, 11, 4),
            "reason": "Personal reasons",
            "station_leave_details": "",
        }
        data.update(overrides)
        return data

    def test_rejects_end_date_before_start_date(self):
        serializer = LeaveApplicationSerializer(data=self.payload(
            start_date=date(2026, 11, 5), end_date=date(2026, 11, 4)
        ))
        self.assertFalse(serializer.is_valid())
        self.assertIn("end_date", serializer.errors)

    def test_rejects_non_positive_employee_id(self):
        serializer = LeaveApplicationSerializer(data=self.payload(employee_id=0))
        self.assertFalse(serializer.is_valid())
        self.assertIn("employee_id", serializer.errors)

    def test_rejects_blank_reason(self):
        serializer = LeaveApplicationSerializer(data=self.payload(reason="   "))
        self.assertFalse(serializer.is_valid())
        self.assertIn("reason", serializer.errors)

    def test_accepts_valid_application_payload(self):
        serializer = LeaveApplicationSerializer(data=self.payload())
        self.assertTrue(serializer.is_valid(), serializer.errors)
