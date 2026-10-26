"""API rules: no self-review, balance checked on apply, balance deducted on approve."""
from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.elm.models import LeaveApplication, LeaveBalance

pytestmark = pytest.mark.django_db

APPLY_URL = "/api/v1/elm/requests"
DECISION_URL = "/api/v1/elm/requests/{pk}/decision"

EMPLOYEE_PERMS = (
    "leave_elm.request.view_self",
    "leave_elm.request.apply",
    "leave_elm.balance.view_self",
)
REVIEWER_PERMS = (*EMPLOYEE_PERMS, "leave_elm.request.review")


def _as(stub_iam, uid, perms):
    stub_iam(make_session(user_id=uid, kind="staff", modules=("leave_elm",),
                          permissions=perms))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token abc")
    return client


def _balance(uid, entitled, used="0"):
    return LeaveBalance.objects.create(
        user_id=uid, year=2026, category="CL",
        entitled_days=Decimal(entitled), used_days=Decimal(used))


def _pending(uid, start=date(2026, 11, 2), end=date(2026, 11, 4), part="full"):
    return LeaveApplication.objects.create(
        user_id=uid, category="CL", start_date=start, end_date=end,
        part_of_day=part, reason="test")


def _apply(client, start="2026-11-02", end="2026-11-04", part="full"):
    return client.post(APPLY_URL, {
        "category": "CL", "start_date": start, "end_date": end,
        "part_of_day": part, "reason": "test",
    }, format="json")


def _decide(client, pk, decision="approve"):
    return client.post(DECISION_URL.format(pk=pk), {"decision": decision},
                       format="json")


def test_reviewer_cannot_approve_own_request(stub_iam):
    _balance(7, "10")
    app = _pending(7)
    client = _as(stub_iam, 7, REVIEWER_PERMS)

    response = _decide(client, app.pk)

    assert response.status_code == 403
    app.refresh_from_db()
    assert app.status == "pending"


def test_reviewer_cannot_reject_own_request_either(stub_iam):
    app = _pending(7)
    client = _as(stub_iam, 7, REVIEWER_PERMS)

    assert _decide(client, app.pk, "reject").status_code == 403
    app.refresh_from_db()
    assert app.status == "pending"


def test_reviewer_can_still_approve_someone_elses_request(stub_iam):
    _balance(8, "10")
    app = _pending(8)
    client = _as(stub_iam, 7, REVIEWER_PERMS)

    assert _decide(client, app.pk).status_code == 200
    app.refresh_from_db()
    assert app.status == "approved"


def test_apply_refused_when_balance_too_low(stub_iam):
    _balance(8, "2")
    client = _as(stub_iam, 8, EMPLOYEE_PERMS)

    response = _apply(client)  # 3 days requested, 2 available

    assert response.status_code == 400
    assert not LeaveApplication.objects.exists()


def test_apply_allowed_when_balance_is_enough(stub_iam):
    _balance(8, "3")
    client = _as(stub_iam, 8, EMPLOYEE_PERMS)

    assert _apply(client).status_code == 201


def test_approval_deducts_the_days(stub_iam):
    balance = _balance(8, "5")
    app = _pending(8)  # 3 days
    client = _as(stub_iam, 7, REVIEWER_PERMS)

    assert _decide(client, app.pk).status_code == 200
    balance.refresh_from_db()
    assert balance.used_days == Decimal("3")


def test_half_day_approval_deducts_half(stub_iam):
    balance = _balance(8, "5")
    app = _pending(8, end=date(2026, 11, 2), part="first_half")
    client = _as(stub_iam, 7, REVIEWER_PERMS)

    _decide(client, app.pk)

    balance.refresh_from_db()
    assert balance.used_days == Decimal("0.5")


def test_rejection_does_not_deduct(stub_iam):
    balance = _balance(8, "5")
    app = _pending(8)
    client = _as(stub_iam, 7, REVIEWER_PERMS)

    assert _decide(client, app.pk, "reject").status_code == 200
    balance.refresh_from_db()
    assert balance.used_days == Decimal("0")
