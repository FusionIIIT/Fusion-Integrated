"""Tests for year-end automated processing (BR-EL-002, BR-EL-005..008, EL-UC-020, WF-EL-07)."""

from decimal import Decimal
from io import StringIO

import pytest
from django.core.management import call_command

from modules.leave.models import LeaveBalance, LeaveLedgerEntry
from modules.leave.services.year_end import run_year_end_processing


@pytest.mark.django_db
def test_year_end_processing_faculty(stub_iam, user_ref):
    faculty_id = 701
    stub_iam(users={faculty_id: user_ref(faculty_id, kind="faculty")})

    # Faculty with 4 CL, 1 RH, 5 SCL, 10 EL, 30 VL, 12 COL
    old_bal = LeaveBalance.objects.create(
        user_id=faculty_id,
        year=2026,
        is_faculty=True,
        cl_balance=Decimal("4.0"),
        rh_balance=Decimal("1.0"),
        scl_balance=Decimal("5.0"),
        el_balance=Decimal("10.0"),
        vl_balance=Decimal("30.0"),
        col_balance=Decimal("12.0"),
    )

    count = run_year_end_processing(2026)
    assert count >= 1

    old_bal.refresh_from_db()
    assert old_bal.year_end_processed is True
    assert old_bal.cl_balance == Decimal("0.0")
    assert old_bal.rh_balance == Decimal("0.0")
    assert old_bal.scl_balance == Decimal("0.0")
    assert old_bal.vl_balance == Decimal("0.0")

    # Check next year balance
    next_bal = LeaveBalance.objects.get(user_id=faculty_id, year=2027)
    assert next_bal.is_faculty is True
    # New CL, RH, SCL grants: 8, 2, 15
    assert next_bal.cl_balance == Decimal("8.0")
    assert next_bal.rh_balance == Decimal("2.0")
    assert next_bal.scl_balance == Decimal("15.0")
    # VL converted to EL at 2:1 -> 30 VL becomes 15 EL. Carried EL = 10 + 15 = 25 EL.
    assert next_bal.el_balance == Decimal("25.0")
    # Fresh VL grant = 60
    assert next_bal.vl_balance == Decimal("60.0")
    # COL carried forward = 12 + fresh grant (20) = 32
    assert next_bal.col_balance == Decimal("32.0")

    # Verify ledger entries
    vl_conv = LeaveLedgerEntry.objects.filter(
        balance=old_bal, category="VL", entry_type="conversion"
    ).first()
    assert vl_conv is not None
    assert "Converted 30.0 VL to 15 EL" in vl_conv.remarks


@pytest.mark.django_db
def test_year_end_processing_staff_non_faculty(stub_iam, user_ref):
    staff_id = 702
    stub_iam(users={staff_id: user_ref(staff_id, kind="staff")})

    # Staff with 2 CL, 0 RH, 15 EL, 0 VL, 10 COL
    old_bal = LeaveBalance.objects.create(
        user_id=staff_id,
        year=2026,
        is_faculty=False,
        cl_balance=Decimal("2.0"),
        rh_balance=Decimal("0.0"),
        scl_balance=Decimal("0.0"),
        el_balance=Decimal("15.0"),
        vl_balance=Decimal("0.0"),
        col_balance=Decimal("10.0"),
    )

    run_year_end_processing(2026)

    old_bal.refresh_from_db()
    assert old_bal.year_end_processed is True

    next_bal = LeaveBalance.objects.get(user_id=staff_id, year=2027)
    assert next_bal.is_faculty is False
    assert next_bal.cl_balance == Decimal("8.0")
    # Staff EL = carried 15 + new 30 = 45
    assert next_bal.el_balance == Decimal("45.0")
    assert next_bal.vl_balance == Decimal("0.0")
    # Staff COL = carried 10 + new 20 = 30
    assert next_bal.col_balance == Decimal("30.0")


@pytest.mark.django_db
def test_run_leave_year_end_command(stub_iam, user_ref):
    staff_id = 703
    stub_iam(users={staff_id: user_ref(staff_id, kind="staff")})
    LeaveBalance.objects.create(
        user_id=staff_id,
        year=2026,
        is_faculty=False,
        cl_balance=Decimal("1.0"),
    )

    out = StringIO()
    call_command("run_leave_year_end", "--year", "2026", stdout=out)
    output = out.getvalue()
    assert "Processed year=2026" in output
