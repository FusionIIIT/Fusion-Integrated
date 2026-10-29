"""API tests for ELM module endpoints."""
import datetime
from decimal import Decimal
import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.elm.models import LeaveBalance, LeaveRequest
from modules.elm.services import balances as balance_service

pytestmark = pytest.mark.django_db


def _client(stub_iam, **kw):
    stub_iam(make_session(**kw))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c


def test_unauthenticated_or_unregistered_module_denied(stub_iam):
    # User without 'elm' module grant
    c = _client(stub_iam, user_id=999, modules=("placement_cell",), permissions=())
    res = c.get("/api/v1/elm/leaves")
    assert res.status_code == 403


def test_apply_for_cl_and_retrieve(stub_iam):
    user_id = 1001
    balance_service.credit_annual_entitlement(user_id=user_id, year=2026, is_faculty=False)

    c = _client(
        stub_iam,
        user_id=user_id,
        modules=("elm",),
        permissions=("elm.leave.apply", "elm.leave.view_self"),
        roles=("employee",),
    )

    # 1. Apply for leave
    payload = {
        "category": "CL",
        "start_date": "2026-11-02",
        "end_date": "2026-11-02",
        "half": "full",
        "purpose": "Personal work",
        "submit": True,
    }
    res = c.post("/api/v1/elm/leaves", payload, format="json")
    assert res.status_code == 201
    data = res.json()
    assert data["category"] == "CL"
    assert data["status"] == "awaiting_unit_head"
    assert Decimal(str(data["days_counted"])) == Decimal("1.0")

    leave_id = data["id"]

    # 2. Get list of leaves
    list_res = c.get("/api/v1/elm/leaves")
    assert list_res.status_code == 200
    rows = list_res.json()["results"]
    assert len(rows) == 1
    assert rows[0]["id"] == leave_id

    # 3. Get detail
    detail_res = c.get(f"/api/v1/elm/leaves/{leave_id}")
    assert detail_res.status_code == 200
    assert detail_res.json()["id"] == leave_id


def test_substitute_workflow_api(stub_iam):
    emp_id = 1002
    sub_id = 1003
    balance_service.credit_annual_entitlement(user_id=emp_id, year=2026, is_faculty=False)

    emp_client = _client(
        stub_iam,
        user_id=emp_id,
        modules=("elm",),
        permissions=("elm.leave.apply", "elm.leave.view_self"),
    )

    # Apply for EL with substitute
    payload = {
        "category": "EL",
        "start_date": "2026-11-09",
        "end_date": "2026-11-13",
        "purpose": "Vacation",
        "substitute_id": sub_id,
        "submit": True,
    }
    create_res = emp_client.post("/api/v1/elm/leaves", payload, format="json")
    assert create_res.status_code == 201
    leave_id = create_res.json()["id"]
    assert create_res.json()["status"] == "awaiting_substitute"

    # Substitute views substitute requests queue
    sub_client = _client(
        stub_iam,
        user_id=sub_id,
        modules=("elm",),
        permissions=("elm.leave.respond_substitute",),
    )
    sub_queue = sub_client.get("/api/v1/elm/substitute/requests")
    assert sub_queue.status_code == 200
    assert len(sub_queue.json()["results"]) == 1

    # Substitute accepts
    sub_resp = sub_client.post(
        f"/api/v1/elm/leaves/{leave_id}/substitute",
        {"accept": True, "reason": "Will handle lectures."},
        format="json",
    )
    assert sub_resp.status_code == 200
    assert sub_resp.json()["status"] == "awaiting_unit_head"
    assert sub_resp.json()["substitute_accepted"] is True


def test_unit_head_and_sanction_api(stub_iam):
    emp_id = 1004
    uh_id = 2001
    sanctioner_id = 3001
    balance_service.credit_annual_entitlement(user_id=emp_id, year=2026, is_faculty=False)

    # Create request awaiting unit head
    req = LeaveRequest.objects.create(
        user_id=emp_id,
        category="EL",
        status="awaiting_unit_head",
        start_date=datetime.date(2026, 11, 23),
        end_date=datetime.date(2026, 11, 27),
        days_counted=Decimal("5.0"),
    )

    # Unit head recommends
    uh_client = _client(
        stub_iam,
        user_id=uh_id,
        modules=("elm",),
        permissions=("elm.leave.approve", "elm.leave.view_all"),
    )
    review_res = uh_client.post(
        f"/api/v1/elm/leaves/{req.pk}/review",
        {"action": "recommend", "reason": "Approved and recommended."},
        format="json",
    )
    assert review_res.status_code == 200
    assert review_res.json()["status"] == "awaiting_sanction"
    assert review_res.json()["unit_head_recommendation"] == "recommended"

    # Sanctioning authority approves
    sanction_client = _client(
        stub_iam,
        user_id=sanctioner_id,
        modules=("elm",),
        permissions=("elm.leave.approve", "elm.leave.view_all", "elm.leave.report"),
    )
    sanction_res = sanction_client.post(
        f"/api/v1/elm/leaves/{req.pk}/sanction",
        {"approve": True, "reason": "Granted in full."},
        format="json",
    )
    assert sanction_res.status_code == 200
    assert sanction_res.json()["status"] == "approved"

    # Check balance deducted
    bal = LeaveBalance.objects.get(user_id=emp_id, category="EL", year=2026)
    assert bal.used == Decimal("5.0")
    assert bal.available == 25.0


def test_my_balances_api(stub_iam):
    user_id = 1005
    balance_service.credit_annual_entitlement(user_id=user_id, year=2026, is_faculty=False)

    c = _client(
        stub_iam,
        user_id=user_id,
        modules=("elm",),
        permissions=("elm.leave.view_self",),
    )
    res = c.get("/api/v1/elm/balances/my?year=2026")
    assert res.status_code == 200
    rows = res.json()["results"]
    categories = {r["category"]: r["available"] for r in rows}
    assert categories["CL"] == 8.0
    assert categories["RH"] == 2.0
    assert categories["EL"] == 30.0
