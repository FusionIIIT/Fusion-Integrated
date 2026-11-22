import json
from datetime import date
from decimal import Decimal
from io import StringIO

import pytest
from django.core.management import call_command
from rest_framework.exceptions import ValidationError

from modules.elm.models import LeaveBalance, LeaveEvent, LeaveRequest, LeaveType
from modules.elm.tests.test_submission import seed
from modules.elm.year_end import rollover_employee

# test_year_end_processing.py


pytestmark = pytest.mark.django_db


def setup_accounts():
    leave_type, _applicant = seed()
    closing = {
        "CL": Decimal("3"),
        "RH": Decimal("1"),
        "SCL": Decimal("4"),
        "EL": Decimal("7.5"),
        "COL": Decimal("2"),
    }
    for code, value in closing.items():
        category = leave_type if code == "CL" else LeaveType.objects.create(type=code)
        LeaveBalance.objects.create(
            employee=101, leave_type=category, year=2025, employee_kind="staff", balance=value
        )
    return closing


def test_rollover_preserves_closing_and_is_idempotent():
    closing = setup_accounts()
    result = rollover_employee(101, 2025, 201)
    assert result["status"] == "processed"

    openings = dict(
        LeaveBalance.objects.filter(employee=101, year=2026).values_list(
            "leave_type__type", "balance"
        )
    )
    expected = {
        "CL": Decimal("8"),
        "RH": Decimal("2"),
        "SCL": Decimal("15"),
        "EL": Decimal("37.5"),
        "COL": Decimal("22"),
    }
    assert openings == expected

    closing_after = dict(
        LeaveBalance.objects.filter(employee=101, year=2025).values_list(
            "leave_type__type", "balance"
        )
    )
    assert closing_after == closing

    result = rollover_employee(101, 2025, 201)
    assert result["status"] == "already_processed"

    assert LeaveBalance.objects.filter(employee=101, year=2026).count() == 5
    events = LeaveEvent.objects.filter(employee=101, action="YEAR_END_ROLLED_OVER")
    assert events.count() == 1


@pytest.mark.parametrize("case", ["duplicate", "opening", "pending", "negative"])
def test_rollover_rejects_ambiguous_accounts(case):

    setup_accounts()
    cl = LeaveType.objects.get(type="CL")

    if case == "duplicate":
        LeaveBalance.objects.create(
            employee=101, leave_type=cl, year=2025, employee_kind="staff", balance=3
        )
    elif case == "opening":
        LeaveBalance.objects.create(
            employee=101, leave_type=cl, year=2026, employee_kind="staff", balance=1
        )
    elif case == "pending":
        LeaveRequest.objects.create(
            employee=101,
            leave_type=cl,
            start_date=date(2025, 11, 3),
            end_date=date(2025, 11, 3),
            purpose="Pending",
            status="PENDING",
        )
    elif case == "negative":
        LeaveBalance.objects.filter(employee=101, year=2025, leave_type=cl).update(balance=-1)

    with pytest.raises(ValidationError):
        rollover_employee(101, 2025, 201)

    assert not LeaveEvent.objects.filter(employee=101, action="YEAR_END_ROLLED_OVER").exists()

    if case == "opening":
        assert (
            LeaveBalance.objects.filter(employee=101, year=2026, employee_kind="staff").count() == 1
        )
    else:
        assert (
            LeaveBalance.objects.filter(employee=101, year=2026, employee_kind="staff").count() == 0
        )


def test_faculty_rollover_keeps_fractional_conversion():
    setup_accounts()
    from modules.directory.models import UserRef

    UserRef.objects.filter(user_id=101).update(kind="faculty")
    LeaveBalance.objects.filter(employee=101, year=2025).update(employee_kind="faculty")
    type_vl = LeaveType.objects.create(type="VL")
    LeaveBalance.objects.create(employee=101, year=2025, leave_type=type_vl, balance=Decimal("5"))
    LeaveBalance.objects.filter(employee=101, year=2025).update(employee_kind="faculty")
    rollover_employee(101, 2025, 201)
    el_balance = LeaveBalance.objects.get(employee=101, year=2026, leave_type__type="EL")
    vl_balance = LeaveBalance.objects.get(employee=101, year=2026, leave_type=type_vl)
    assert el_balance.balance == Decimal("10")
    assert vl_balance.balance == Decimal("60")


def test_closed_year_cannot_be_reused():
    setup_accounts()
    rollover_employee(101, 2025, 201)
    from rest_framework.exceptions import ValidationError

    from modules.elm.validation import account

    cl = LeaveType.objects.get(type="CL")
    with pytest.raises(ValidationError):
        account(101, cl, 2025, "staff")
    cl_balance = LeaveBalance.objects.get(employee=101, year=2025, leave_type=cl)
    assert cl_balance.balance == Decimal("3")


def test_rollover_command_reports_exceptions():
    setup_accounts()
    out = StringIO()
    call_command("elm_rollover_year", year=2025, employee=101, stdout=out)
    payload = json.loads(out.getvalue())
    assert payload["exceptions"] == []
    assert payload["results"][0]["status"] == "processed"
    assert LeaveBalance.objects.filter(employee=101, year=2026).count() == 5
