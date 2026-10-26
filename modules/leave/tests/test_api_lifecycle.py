"""Approved-leave lifecycle: cancellation and resumption (EL-UC-008/010/011)."""

from datetime import date
from decimal import Decimal

import pytest

from modules.leave.models import LeaveBalance, LeaveRequest

pytestmark = pytest.mark.django_db

URL = "/api/v1/leave"


def _approved(unit, user_id=101, start=date(2030, 3, 4), end=date(2030, 3, 5), days="2"):
    return LeaveRequest.objects.create(
        user_id=user_id,
        category="CL",
        start_date=start,
        end_date=end,
        days=Decimal(days),
        purpose="x",
        unit=unit,
        status="approved",
        substitute_status="not_required",
    )


def test_cancel_future_approved_leave_refunds_balance(as_user, unit, balances):
    """BR-EL-023: approved leave that has not started can be cancelled; days come back."""
    LeaveBalance.objects.filter(user_id=101, year=2030, category="CL").update(used=Decimal("2"))
    req = _approved(unit)
    r = as_user(101, "leave.request.create").post(
        f"{URL}/requests/{req.id}/cancel", {}, format="json"
    )
    assert r.status_code == 200, r.content
    assert r.json()["status"] == "cancelled"
    assert LeaveBalance.objects.get(user_id=101, year=2030, category="CL").used == Decimal("0")


def test_cannot_cancel_leave_that_has_started(as_user, unit):
    """BR-EL-023: approved leave that has started cannot be cancelled."""
    req = _approved(unit, start=date(2020, 1, 6), end=date(2020, 1, 7))
    r = as_user(101, "leave.request.create").post(
        f"{URL}/requests/{req.id}/cancel", {}, format="json"
    )
    assert r.status_code >= 400


def test_cannot_cancel_someone_elses_leave(as_user, unit):
    """BR-EL-023: cannot cancel someone else's approved leave."""
    req = _approved(unit)
    r = as_user(202, "leave.request.create").post(
        f"{URL}/requests/{req.id}/cancel", {}, format="json"
    )
    assert r.status_code >= 400


def test_submit_resumption_late(as_user, unit):
    """EL-UC-010, BR-EL-028: submit resumption late."""
    req = _approved(unit)
    r = as_user(101, "leave.request.create").post(
        f"{URL}/requests/{req.id}/resumption", {"resumed_on": "2030-03-08"}, format="json"
    )
    assert r.status_code in (200, 201)
    assert r.json()["outcome"] == "late"


def test_submit_resumption_normal(as_user, unit):
    """EL-UC-010: submit resumption normal."""
    req = _approved(unit)
    r = as_user(101, "leave.request.create").post(
        f"{URL}/requests/{req.id}/resumption", {"resumed_on": "2030-03-06"}, format="json"
    )
    assert r.status_code in (200, 201)
    assert r.json()["outcome"] == "normal"


def test_unit_head_accepts_resumption(as_user, unit):
    """EL-UC-011: unit head accepts resumption."""
    req = _approved(unit)
    r = as_user(101, "leave.request.create").post(
        f"{URL}/requests/{req.id}/resumption", {"resumed_on": "2030-03-06"}, format="json"
    )
    assert r.status_code in (200, 201)
    resumption_id = r.json()["id"]
    r = as_user(500, "leave.resumption.verify").get(f"{URL}/resumptions")
    assert resumption_id in {x["id"] for x in r.json()["results"]}
    r = as_user(500, "leave.resumption.verify").post(
        f"{URL}/resumptions/{resumption_id}/review", {"accept": True}, format="json"
    )
    assert r.status_code == 200
    assert r.json()["status"] == "accepted"


def test_resumption_needs_approved_leave(as_user, unit):
    """EL-UC-011: resumption needs approved leave."""
    req = LeaveRequest.objects.create(
        user_id=101,
        category="CL",
        start_date=date(2030, 3, 4),
        end_date=date(2030, 3, 5),
        days=Decimal("2"),
        purpose="x",
        unit=unit,
        status="unit_review",
        substitute_status="not_required",
    )
    r = as_user(101, "leave.request.create").post(
        f"{URL}/requests/{req.id}/resumption", {"resumed_on": "2030-03-06"}, format="json"
    )
    assert r.status_code >= 400


def test_employee_sees_own_balances(as_user, balances):
    """EL-UC-012: the balances endpoint lists the caller's own six categories, nobody else's."""
    r = as_user(101, "leave.balance.view").get(f"{URL}/balances")
    assert r.status_code == 200, r.content
    rows = r.json()
    assert {b["user_id"] for b in rows} == {101}
    assert {"CL", "RH", "SCL", "EL", "COL", "VL"} <= {b["category"] for b in rows}
