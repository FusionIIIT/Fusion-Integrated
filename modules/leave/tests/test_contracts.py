"""Tests for Leave module public contract surface (contracts.py)."""

from datetime import date
from decimal import Decimal

import pytest

from modules.leave.contracts import get_leave_status
from modules.leave.models import LeaveBalance
from modules.leave.services import apply_for_leave, review_by_unit_head


@pytest.mark.django_db
def test_get_leave_status_contract():
    user1 = 1001
    user2 = 1002
    unit_head = 1003
    today = date(2026, 11, 2)

    # user1 has approved CL from Nov 2 to Nov 3
    LeaveBalance.objects.create(user_id=user1, year=2026, cl_balance=Decimal("8.0"))
    app = apply_for_leave(
        user_id=user1,
        category="CL",
        start_date=today,
        end_date=date(2026, 11, 3),
        purpose="Dentist appointment",
        unit_head_user_id=unit_head,
    )
    review_by_unit_head(
        reviewer_user_id=unit_head,
        application_id=app.pk,
        recommended=True,
    )

    # user2 has no leave
    status_map = get_leave_status([user1, user2], on_date=today)

    assert user1 in status_map
    assert status_map[user1].is_on_leave is True
    assert status_map[user1].category == "CL"
    assert status_map[user1].end_date == date(2026, 11, 3)

    assert user2 in status_map
    assert status_map[user2].is_on_leave is False
    assert status_map[user2].category is None

    # On Nov 10, user1 is no longer on leave
    later_map = get_leave_status([user1], on_date=date(2026, 11, 10))
    assert later_map[user1].is_on_leave is False

    # Empty query
    assert get_leave_status([]) == {}
