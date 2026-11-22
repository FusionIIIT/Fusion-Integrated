"""Tests for recording offline-sanctioned leave (BR-EL-029, BR-EL-037, EL-UC-016, WF-EL-06)."""

from datetime import date
from decimal import Decimal

import pytest

from core.api.exceptions import BadRequestError, ConflictError
from modules.leave.models import LeaveActionHistory, LeaveBalance, LeaveLedgerEntry
from modules.leave.services.offline import record_offline_leave


@pytest.mark.django_db
def test_record_offline_leave_success(stub_iam, user_ref):
    employee_id = 801
    admin_id = 802
    stub_iam(users={employee_id: user_ref(employee_id, kind="staff")})

    # Monday Nov 2 to Friday Nov 6, 2026 = 5 days EL
    start = date(2026, 11, 2)
    end = date(2026, 11, 6)

    bal = LeaveBalance.objects.create(
        user_id=employee_id,
        year=2026,
        is_faculty=False,
        el_balance=Decimal("30.0"),
    )

    app = record_offline_leave(
        admin_user_id=admin_id,
        employee_user_id=employee_id,
        category="EL",
        start_date=start,
        end_date=end,
        days_count=Decimal("5.0"),
        offline_reference_no="ESTT/2026/EL/042",
        offline_sanction_date=date(2026, 10, 25),
        purpose="Attending training seminar",
    )

    assert app.status == "approved"
    assert app.offline_reference_no == "ESTT/2026/EL/042"
    assert app.offline_sanction_date == date(2026, 10, 25)
    assert app.days_count == Decimal("5.0")

    bal.refresh_from_db()
    assert bal.el_balance == Decimal("25.0")  # 30 - 5 = 25

    # Check ledger
    entry = LeaveLedgerEntry.objects.filter(balance=bal, category="EL", entry_type="debit").first()
    assert entry is not None
    assert entry.change_amount == Decimal("-5.0")
    assert "Offline sanction" in entry.remarks

    # Check action history (synchronization, not approval workflow)
    action = LeaveActionHistory.objects.filter(application=app).first()
    assert action is not None
    assert action.action == "offline_synchronized"
    assert action.actor_user_id == admin_id


@pytest.mark.django_db
def test_record_offline_leave_missing_reference(stub_iam, user_ref):
    employee_id = 803
    stub_iam(users={employee_id: user_ref(employee_id, kind="staff")})

    LeaveBalance.objects.create(user_id=employee_id, year=2026, el_balance=Decimal("30.0"))

    with pytest.raises(BadRequestError) as exc_info:
        record_offline_leave(
            admin_user_id=802,
            employee_user_id=employee_id,
            category="EL",
            start_date=date(2026, 11, 2),
            end_date=date(2026, 11, 4),
            days_count=Decimal("3.0"),
            offline_reference_no="   ",
            offline_sanction_date=date(2026, 10, 25),
            purpose="Training",
        )
    assert exc_info.value.code == "missing_reference"


@pytest.mark.django_db
def test_record_offline_leave_insufficient_balance(stub_iam, user_ref):
    employee_id = 804
    stub_iam(users={employee_id: user_ref(employee_id, kind="staff")})

    LeaveBalance.objects.create(user_id=employee_id, year=2026, el_balance=Decimal("2.0"))

    with pytest.raises(ConflictError) as exc_info:
        record_offline_leave(
            admin_user_id=802,
            employee_user_id=employee_id,
            category="EL",
            start_date=date(2026, 11, 2),
            end_date=date(2026, 11, 6),
            days_count=Decimal("5.0"),
            offline_reference_no="REF-101",
            offline_sanction_date=date(2026, 10, 25),
            purpose="Training",
        )
    assert exc_info.value.code == "insufficient_balance"
