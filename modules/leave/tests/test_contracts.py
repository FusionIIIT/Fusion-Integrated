"""The contract other modules see (plural, no singular lookup)."""
from __future__ import annotations

from datetime import date

import pytest

from modules.leave import contracts
from modules.leave.models import LeaveRequest

pytestmark = pytest.mark.django_db


def test_get_leave_status_is_plural_and_uses_the_actual_return(
        stub_iam, desks):
    LeaveRequest.objects.create(
        user_id=9100, kind="new", source="elm", category="el",
        status="approved", start_date=date(2026, 10, 20),
        end_date=date(2026, 10, 24), year=2026, chargeable_days=5)
    # A resumption review moved the real last day earlier.
    LeaveRequest.objects.create(
        user_id=9001, kind="new", source="elm", category="cl",
        status="approved", start_date=date(2026, 10, 21),
        end_date=date(2026, 10, 23), actual_end_date=date(2026, 10, 21),
        year=2026, chargeable_days=1)

    status = contracts.get_leave_status([9100, 9001, 9999],
                                        date(2026, 10, 21))
    assert status[9100].on_leave is True
    assert status[9100].until == date(2026, 10, 24)
    assert status[9100].categories == ("el",)
    # On the 22nd the second person is NOT away: actual return was the 21st.
    status = contracts.get_leave_status([9100, 9001], date(2026, 10, 22))
    assert status[9001].on_leave is False
    assert status[9100].on_leave is True


def test_rejected_and_pending_do_not_count(stub_iam, desks):
    LeaveRequest.objects.create(
        user_id=9100, kind="new", source="elm", category="cl",
        status="rejected", start_date=date(2026, 10, 20),
        end_date=date(2026, 10, 24), year=2026, chargeable_days=5)
    LeaveRequest.objects.create(
        user_id=9101, kind="new", source="elm", category="cl",
        status="awaiting_unit_head_review", start_date=date(2026, 10, 20),
        end_date=date(2026, 10, 24), year=2026, chargeable_days=5)
    status = contracts.get_leave_status([9100, 9101], date(2026, 10, 21))
    assert status[9100].on_leave is False
    assert status[9101].on_leave is False


def test_empty_input_is_empty_output(stub_iam, desks):
    assert contracts.get_leave_status([], date(2026, 10, 21)) == {}
