from datetime import date

import pytest
from django.core.exceptions import ValidationError

from modules.elm.models import Employee, LeaveRequest


@pytest.mark.django_db
def test_leave_request_duration_is_inclusive():
    employee = Employee.objects.create(name="Test Employee", department="Engineering")
    leave = LeaveRequest(
        employee=employee,
        start_date=date(2026, 10, 12),
        end_date=date(2026, 10, 14),
        reason="Personal work",
    )
    assert leave.duration_days == 3


@pytest.mark.django_db
def test_leave_request_rejects_end_before_start():
    employee = Employee.objects.create(name="Test Employee", department="Engineering")
    leave = LeaveRequest(
        employee=employee,
        start_date=date(2026, 10, 14),
        end_date=date(2026, 10, 12),
        reason="Personal work",
    )
    with pytest.raises(ValidationError) as exc:
        leave.full_clean()
    assert "end_date" in exc.value.message_dict
