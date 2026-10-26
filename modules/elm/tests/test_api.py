import datetime
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.elm.models import LeaveApplication, LeaveBalance

pytestmark = pytest.mark.django_db


def test_unauthenticated_request_is_401():
    r = APIClient().get("/api/v1/elm/applications")
    assert r.status_code == 401


def test_missing_module_grant_is_403(stub_iam):
    # Principal without "elm" module grant
    stub_iam(
        make_session(user_id=101, modules=("placement_cell",), permissions=("elm.leave.view_self",))
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    r = c.get("/api/v1/elm/applications")
    assert r.status_code == 403


def test_apply_and_list_leave_applications(stub_iam):
    stub_iam(
        make_session(
            user_id=101,
            modules=("elm",),
            permissions=("elm.leave.view_self", "elm.leave.apply"),
            active_role="faculty",
        )
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")

    # Seed balance
    LeaveBalance.objects.create(
        user_id=101,
        year=2026,
        leave_category="CL",
        credited=Decimal("8.0"),
        used=Decimal("0.0"),
    )

    # 1. Apply for single day CL
    payload = {
        "leave_category": "CL",
        "start_date": "2026-11-02",
        "end_date": "2026-11-02",
        "reason": "Personal urgent work",
        "half_day": False,
        "station_leave": False,
        "substitute_required": False,
    }
    r = c.post("/api/v1/elm/applications", payload, format="json")
    assert r.status_code == 201
    data = r.json()
    assert data["leave_category"] == "CL"
    assert data["status"] == "awaiting_unit_head"
    app_id = data["id"]

    # 2. List own applications
    r_list = c.get("/api/v1/elm/applications")
    assert r_list.status_code == 200
    apps = r_list.json()
    assert len(apps) >= 1
    assert apps[0]["id"] == app_id

    # 3. Withdraw pending application (BR-EL-022)
    r_withdraw = c.post(f"/api/v1/elm/applications/{app_id}/withdraw")
    assert r_withdraw.status_code == 200
    assert r_withdraw.json()["status"] == "withdrawn"


def test_substitute_workflow(stub_iam):
    applicant_id = 101
    substitute_id = 202

    # Seed applicant balance
    LeaveBalance.objects.create(
        user_id=applicant_id,
        year=2026,
        leave_category="CL",
        credited=Decimal("8.0"),
        used=Decimal("0.0"),
    )

    # Applicant applies with substitute
    stub_iam(
        make_session(
            user_id=applicant_id,
            modules=("elm",),
            permissions=("elm.leave.view_self", "elm.leave.apply"),
            active_role="faculty",
        )
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")

    payload = {
        "leave_category": "CL",
        "start_date": "2026-11-03",
        "end_date": "2026-11-03",
        "reason": "Conference",
        "substitute_required": True,
        "substitute_id": substitute_id,
    }
    r = c.post("/api/v1/elm/applications", payload, format="json")
    assert r.status_code == 201
    app_id = r.json()["id"]
    assert r.json()["status"] == "awaiting_substitute"

    # Substitute logs in and responds
    stub_iam(
        make_session(
            user_id=substitute_id,
            modules=("elm",),
            permissions=("elm.leave.view_self", "elm.leave.substitute"),
            active_role="faculty",
        )
    )
    c_sub = APIClient()
    c_sub.credentials(HTTP_AUTHORIZATION="Token sub")

    # See pending substitute list
    r_pend = c_sub.get("/api/v1/elm/substitute/pending")
    assert r_pend.status_code == 200
    assert any(a["id"] == app_id for a in r_pend.json())

    # Accept substitute responsibility (BR-EL-015)
    r_accept = c_sub.post(
        f"/api/v1/elm/applications/{app_id}/substitute-respond",
        {"decision": "accepted", "remarks": "Covering your classes"},
        format="json",
    )
    assert r_accept.status_code == 200
    assert r_accept.json()["status"] == "awaiting_unit_head"
    assert r_accept.json()["substitute_status"] == "accepted"


def test_unit_head_approval_and_balance_deduction(stub_iam):
    user_id = 101
    unit_head_id = 505

    # Seed balance
    bal = LeaveBalance.objects.create(
        user_id=user_id,
        year=2026,
        leave_category="CL",
        credited=Decimal("8.0"),
        used=Decimal("0.0"),
    )

    # Create application awaiting Unit Head
    app = LeaveApplication.objects.create(
        user_id=user_id,
        leave_category="CL",
        start_date=datetime.date(2026, 11, 4),
        end_date=datetime.date(2026, 11, 4),
        reason="Family event",
        chargeable_days=Decimal("1.0"),
        status="awaiting_unit_head",
    )

    # Unit head logs in
    stub_iam(
        make_session(
            user_id=unit_head_id,
            modules=("elm",),
            permissions=("elm.leave.view_self", "elm.leave.unit_head_review"),
            active_role="unit_head",
        )
    )
    c_head = APIClient()
    c_head.credentials(HTTP_AUTHORIZATION="Token head")

    # Approve (BR-EL-016: final authority for CL)
    r = c_head.post(
        f"/api/v1/elm/applications/{app.id}/unit-head-review",
        {"action": "approve", "remarks": "Approved by HOD"},
        format="json",
    )
    assert r.status_code == 200
    assert r.json()["status"] == "approved"

    # Verify balance was deducted
    bal.refresh_from_db()
    assert bal.used == Decimal("1.0")
    assert bal.available == Decimal("7.0")
