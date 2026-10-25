"""Tests for ELM Contracts."""
from datetime import date

import pytest

from modules.elm.contracts import (
    get_active_leaves,
    get_employee_on_leave_status,
    get_leave_balances,
)
from modules.elm.models import LeaveCategory
from modules.elm.services import applications as svc

pytestmark = pytest.mark.django_db


@pytest.fixture
def categories():
    svc.ensure_leave_categories()
    return {c.code: c for c in LeaveCategory.objects.all()}


def test_get_leave_balances_contract(categories):
    cl = categories["CL"]
    svc.get_or_create_balance(1001, cl, year=2026)
    svc.get_or_create_balance(2002, cl, year=2026)

    res = get_leave_balances([1001, 2002, 3003], year=2026)
    assert 1001 in res
    assert 2002 in res
    assert 3003 in res
    assert len(res[1001]) >= 1
    assert len(res[3003]) == 0


def test_get_active_leaves_and_status_contract(categories):
    app = svc.submit_leave_application(
        user_id=1001,
        category_code="CL",
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 4),
        reason="Conference",
    )
    svc.review_unit_head(app.id, actor_id=9001, action="approve")

    active = get_active_leaves([1001, 2002])
    assert len(active[1001]) == 1
    assert active[1001][0]["days_count"] == 3.0
    assert len(active[2002]) == 0

    on_leave = get_employee_on_leave_status([1001, 2002], on_date=date(2026, 11, 3))
    assert on_leave[1001] is True
    assert on_leave[2002] is False
