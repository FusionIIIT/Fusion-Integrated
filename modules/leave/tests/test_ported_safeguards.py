"""Traceable regression cases ported from the private ELM rule checks.

These cases are provided for review; they are not recorded as executed by this change.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from conftest import make_principal
from modules.leave import contracts
from modules.leave.domain.counting import count_days
from modules.leave.models import LeaveAccountTransaction, LeaveApplication
from modules.leave.services import accounts, applications, year_end


@pytest.mark.parametrize(
    ("leave_type", "start", "end", "holidays", "half_day", "expected"),
    [
        ("EL", date(2026, 10, 24), date(2026, 10, 26), frozenset(), False, Decimal("3")),
        ("CL", date(2026, 10, 24), date(2026, 10, 26), frozenset(), False, Decimal("1")),
        ("CL", date(2026, 10, 26), date(2026, 10, 26), frozenset(), True, Decimal("0.5")),
        ("SCL", date(2026, 10, 24), date(2026, 10, 26), frozenset(), False, Decimal("1")),
    ],
)
def test_chargeable_days_respect_category_and_workdays(
    leave_type,
    start,
    end,
    holidays,
    half_day,
    expected,
):
    assert count_days(leave_type, start, end, holidays, half_day) == expected


@pytest.mark.parametrize(
    ("leave_type", "start", "end", "half_day"),
    [
        ("CL", date(2026, 10, 24), date(2026, 10, 25), False),
        ("SCL", date(2026, 10, 24), date(2026, 10, 25), False),
        ("CL", date(2026, 10, 24), date(2026, 10, 24), True),
        ("EL", date(2026, 10, 26), date(2026, 10, 26), True),
        ("RH", date(2026, 10, 26), date(2026, 10, 27), False),
        ("CL", datetime(2026, 10, 26), date(2026, 10, 26), False),
    ],
)
def test_invalid_or_ineligible_periods_fail_closed(leave_type, start, end, half_day):
    with pytest.raises(ValueError):
        count_days(leave_type, start, end, half_day=half_day)


@pytest.mark.django_db
def test_ledger_idempotency_key_cannot_be_reused_for_another_amount():
    fields = {
        "user_id": 101,
        "leave_type": "EL",
        "year": 2026,
        "amount": Decimal("12"),
        "transaction_type": "annual_entitlement",
        "source_key": "elm-idempotence:101:2026",
    }
    first = accounts.post(**fields)
    again = accounts.post(**fields)
    assert first.pk == again.pk
    with pytest.raises(ValueError):
        accounts.post(**(fields | {"amount": Decimal("11")}))
    assert LeaveAccountTransaction.objects.filter(source_key=fields["source_key"]).count() == 1


@pytest.mark.django_db
def test_second_cancellation_is_rejected_while_first_is_pending():
    start = timezone.localdate() + timedelta(days=10)
    original = LeaveApplication.objects.create(
        applicant_user_id=101,
        request_kind="new",
        leave_type="CL",
        start_date=start,
        end_date=start,
        requested_days=Decimal("1"),
        status="approved",
        unit_head_user_id=202,
    )
    employee = make_principal(
        user_id=101,
        kind="staff",
        permissions=("leave.application.delete",),
    )
    child = applications.request_cancellation(employee, original)
    assert child.request_kind == "cancellation"
    with pytest.raises(ValidationError):
        applications.request_cancellation(employee, original)


@pytest.mark.django_db
def test_employee_cannot_record_a_future_return():
    today = timezone.localdate()
    leave = LeaveApplication.objects.create(
        applicant_user_id=101,
        request_kind="new",
        leave_type="EL",
        start_date=today - timedelta(days=2),
        end_date=today + timedelta(days=5),
        requested_days=Decimal("8"),
        status="approved",
        final_authority_user_id=202,
    )
    employee = make_principal(user_id=101, kind="staff")
    with pytest.raises(ValidationError):
        applications.record_resumption(employee, leave, today + timedelta(days=1))


@pytest.mark.django_db
def test_duplicate_directory_identities_fail_before_year_end_posting(monkeypatch):
    person = contracts.EmployeeDTO(
        user_id=101,
        display_name="A",
        email="a@example.invalid",
        kind="faculty",
        organizational_unit="CSE",
    )
    monkeypatch.setattr(contracts, "_active_employees", lambda: [person, person])
    with pytest.raises(ValueError):
        year_end.process_year_end(2025)
    assert LeaveAccountTransaction.objects.count() == 0
