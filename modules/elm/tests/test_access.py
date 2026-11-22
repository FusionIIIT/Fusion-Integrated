from datetime import date
from decimal import Decimal

import pytest
from django.db import transaction
from rest_framework.exceptions import ValidationError

from modules.directory.models import UserRef
from modules.elm.models import AuthorityRoute, CalendarDay, LeaveBalance, LeaveType
from modules.elm.validation import account, count_days, locked_employee, resolve_route

pytestmark = pytest.mark.django_db


def setup_rows():
    UserRef.objects.create(user_id=101, username="u101", kind="staff")
    UserRef.objects.create(user_id=201, username="u201", kind="staff")
    UserRef.objects.create(user_id=301, username="u301", kind="faculty")
    leave_type = LeaveType.objects.create(type="CL")
    AuthorityRoute.objects.create(
        employee=101, leave_category="", unit_head=201, higher_authorities=[301]
    )
    return leave_type


def test_count_days_cl():
    start = date(2026, 11, 6)
    end = date(2026, 11, 9)
    assert count_days("CL", start, end) == Decimal("2")
    assert count_days("EL", start, end) == Decimal("4")


def test_count_days_cl_first():
    start = date(2026, 11, 2)
    assert count_days("CL", start, start, half="FIRST") == Decimal("0.5")
    with pytest.raises(ValidationError):
        count_days("EL", start, start, half="FIRST")


def test_count_days_cl_full():
    start = date(2026, 11, 7)  # Saturday
    with pytest.raises(ValidationError):
        count_days("CL", start, start)
    with pytest.raises(ValidationError):
        count_days("CL", start, date(2026, 11, 8), half="FIRST")


def test_calendar_day_rh():
    CalendarDay.objects.create(date=date(2026, 11, 2), kind="RH", published=True)
    assert count_days("RH", date(2026, 11, 2), date(2026, 11, 2)) == Decimal("1")
    with pytest.raises(ValidationError):
        count_days("RH", date(2026, 11, 3), date(2026, 11, 3))


def test_vl_without_source():
    with pytest.raises(ValidationError):
        count_days("VL", date(2026, 11, 2), date(2026, 11, 2))
    CalendarDay.objects.create(
        date=date(2026, 11, 2), kind="VACATION", published=True, source="Academic Calendar"
    )
    assert count_days("VL", date(2026, 11, 2), date(2026, 11, 2)) == Decimal("1")


def test_locked_employee_and_account():
    leave_type = setup_rows()
    with transaction.atomic():
        assert locked_employee(101).user_id == 101
        LeaveBalance.objects.create(employee=101, leave_type=leave_type, year=2026, balance=8)
        assert account(101, leave_type, 2026, "staff").balance == 8
        assert resolve_route(101, "CL") == [201]
        assert resolve_route(101, "EL") == [201, 301]


def test_account_with_multiple_balances():
    leave_type = setup_rows()
    with transaction.atomic():
        LeaveBalance.objects.create(employee=101, leave_type=leave_type, year=2026, balance=8)
        LeaveBalance.objects.create(employee=101, leave_type=leave_type, year=2026, balance=5)
        with pytest.raises(ValidationError):
            account(101, leave_type, 2026, "staff")
