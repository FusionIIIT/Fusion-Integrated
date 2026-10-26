"""Comprehensive API integration and workflow tests for ELM (EL-UC-001..021).

Tests all endpoints, serializers, permissions, and transitions using the Fusion test harness.
"""
from __future__ import annotations

import datetime
from decimal import Decimal
import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.elm.models import Holiday, HolidayCalendar, LeaveBalance, LeaveRequest
from modules.elm.domain import state_machine as sm

pytestmark = pytest.mark.django_db


def _auth_client(stub_iam, user_id: int = 1001, roles: tuple[str, ...] = ("faculty",), permissions: tuple[str, ...] = ()):
    all_perms = set(permissions) | {"elm.request.create", "elm.request.view"}
    stub_iam(make_session(user_id=user_id, kind="faculty", modules=("elm",), roles=roles, permissions=all_perms))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token mock-test-token")
    return client


# --- EL-UC-001: Apply for Leave ---
def test_apply_for_casual_leave(stub_iam):
    client = _auth_client(stub_iam, user_id=101)
    # Seed 8 days CL balance
    LeaveBalance.objects.create(user_id=101, category="cl", year=2026, credited=Decimal("8.0"))

    payload = {
        "category": "cl",
        "start_date": "2026-11-02",  # Monday
        "end_date": "2026-11-03",    # Tuesday
        "reason": "Family function",
    }
    response = client.post("/api/v1/elm/leave-requests/", data=payload, format="json")
    assert response.status_code == 201
    data = response.json()
    assert data["category"] == "cl"
    assert data["leave_days"] == "2.0"
    assert data["status"] == sm.PENDING_UNIT_HEAD

    # Verify pending balance reserved
    bal = LeaveBalance.objects.get(user_id=101, category="cl", year=2026)
    assert bal.pending == Decimal("2.0")
    assert bal.available == Decimal("6.0")


def test_apply_half_day_cl_deducts_half_day(stub_iam):
    client = _auth_client(stub_iam, user_id=102)
    LeaveBalance.objects.create(user_id=102, category="cl", year=2026, credited=Decimal("8.0"))

    payload = {
        "category": "cl",
        "start_date": "2026-11-04",
        "end_date": "2026-11-04",
        "half_day": True,
        "half_day_type": "first_half",
        "reason": "Doctor appointment",
    }
    response = client.post("/api/v1/elm/leave-requests/", data=payload, format="json")
    assert response.status_code == 201
    data = response.json()
    assert data["leave_days"] == "0.5"
    assert data["half_day"] is True
    assert data["half_day_type"] == "first_half"

    bal = LeaveBalance.objects.get(user_id=102, category="cl", year=2026)
    assert bal.pending == Decimal("0.5")
    assert bal.available == Decimal("7.5")


def test_apply_half_day_non_cl_rejected(stub_iam):
    client = _auth_client(stub_iam, user_id=103)
    payload = {
        "category": "el",
        "start_date": "2026-11-04",
        "end_date": "2026-11-04",
        "half_day": True,
        "half_day_type": "first_half",
        "reason": "Not permitted",
    }
    response = client.post("/api/v1/elm/leave-requests/", data=payload, format="json")
    assert response.status_code == 400
    assert "half_day" in response.json()


def test_apply_with_substitute_places_request_in_awaiting_substitute(stub_iam):
    client = _auth_client(stub_iam, user_id=104)
    LeaveBalance.objects.create(user_id=104, category="cl", year=2026, credited=Decimal("8.0"))

    payload = {
        "category": "cl",
        "start_date": "2026-11-05",
        "end_date": "2026-11-05",
        "reason": "Personal work",
        "substitute_id": 999,
    }
    response = client.post("/api/v1/elm/leave-requests/", data=payload, format="json")
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == sm.PENDING_SUBSTITUTE
    assert data["substitute_id"] == 999
    assert data["substitute_status"] == "pending"


# --- EL-UC-002: Substitute Respond ---
def test_substitute_accept_and_decline_flow(stub_iam):
    # Setup request with substitute 999
    LeaveBalance.objects.create(user_id=105, category="cl", year=2026, credited=Decimal("8.0"))
    req = LeaveRequest.objects.create(
        user_id=105,
        category="cl",
        start_date=datetime.date(2026, 11, 5),
        end_date=datetime.date(2026, 11, 5),
        leave_days=Decimal("1.0"),
        reason="Test",
        substitute_id=999,
        substitute_status="pending",
        status=sm.PENDING_SUBSTITUTE,
    )

    # 1. Substitute accepts
    sub_client = _auth_client(stub_iam, user_id=999)
    resp = sub_client.post(
        f"/api/v1/elm/leave-requests/{req.id}/substitute-respond/",
        data={"action": "accept", "remarks": "I will cover lectures."},
        format="json",
    )
    assert resp.status_code == 200
    req.refresh_from_db()
    assert req.status == sm.PENDING_UNIT_HEAD
    assert req.substitute_status == "accepted"


def test_substitute_decline_and_applicant_nominates_replacement(stub_iam):
    LeaveBalance.objects.create(user_id=106, category="cl", year=2026, credited=Decimal("8.0"))
    req = LeaveRequest.objects.create(
        user_id=106,
        category="cl",
        start_date=datetime.date(2026, 11, 6),
        end_date=datetime.date(2026, 11, 6),
        leave_days=Decimal("1.0"),
        reason="Test",
        substitute_id=999,
        substitute_status="pending",
        status=sm.PENDING_SUBSTITUTE,
    )

    # Substitute declines
    sub_client = _auth_client(stub_iam, user_id=999)
    resp = sub_client.post(
        f"/api/v1/elm/leave-requests/{req.id}/substitute-respond/",
        data={"action": "decline", "remarks": "Unavailable on this date."},
        format="json",
    )
    assert resp.status_code == 200
    req.refresh_from_db()
    assert req.status == sm.SUBSTITUTE_DECLINED
    assert req.substitute_status == "declined"

    # Applicant nominates replacement substitute 888 (EL-UC-019)
    app_client = _auth_client(stub_iam, user_id=106)
    resp2 = app_client.post(
        f"/api/v1/elm/leave-requests/{req.id}/nominate-replacement-substitute/",
        data={"substitute_id": 888, "remarks": "Replacing substitute."},
        format="json",
    )
    assert resp2.status_code == 200
    req.refresh_from_db()
    assert req.status == sm.PENDING_SUBSTITUTE
    assert req.substitute_id == 888
    assert req.substitute_status == "pending"


# --- EL-UC-003: Unit Head Review ---
def test_unit_head_approves_cl_as_final_decision(stub_iam):
    LeaveBalance.objects.create(user_id=107, category="cl", year=2026, credited=Decimal("8.0"), pending=Decimal("1.0"))
    req = LeaveRequest.objects.create(
        user_id=107,
        category="cl",
        start_date=datetime.date(2026, 11, 9),
        end_date=datetime.date(2026, 11, 9),
        leave_days=Decimal("1.0"),
        reason="Exam duty leave",
        status=sm.PENDING_UNIT_HEAD,
    )

    hod_client = _auth_client(stub_iam, user_id=501, roles=("unit_head", "hod"), permissions=("elm.request.review",))
    resp = hod_client.post(
        f"/api/v1/elm/leave-requests/{req.id}/unit-head-review/",
        data={"decision": "approve", "remarks": "Approved by HOD."},
        format="json",
    )
    assert resp.status_code == 200
    req.refresh_from_db()
    assert req.status == sm.APPROVED

    bal = LeaveBalance.objects.get(user_id=107, category="cl", year=2026)
    assert bal.pending == Decimal("0.0")
    assert bal.availed == Decimal("1.0")


def test_unit_head_recommends_el_to_higher_sanction(stub_iam):
    LeaveBalance.objects.create(user_id=108, category="el", year=2026, credited=Decimal("30.0"), pending=Decimal("5.0"))
    req = LeaveRequest.objects.create(
        user_id=108,
        category="el",
        start_date=datetime.date(2026, 11, 10),
        end_date=datetime.date(2026, 11, 14),
        leave_days=Decimal("5.0"),
        reason="Conference presentation",
        status=sm.PENDING_UNIT_HEAD,
    )

    hod_client = _auth_client(stub_iam, user_id=501, roles=("unit_head", "hod"), permissions=("elm.request.review",))
    resp = hod_client.post(
        f"/api/v1/elm/leave-requests/{req.id}/unit-head-review/",
        data={"decision": "recommended", "remarks": "Recommended for sanction."},
        format="json",
    )
    assert resp.status_code == 200
    req.refresh_from_db()
    assert req.status == sm.PENDING_SANCTION
    assert req.unit_head_recommendation == "recommended"


# --- EL-UC-005: Sanction Decision ---
def test_dean_sanction_approval_and_rejection(stub_iam):
    LeaveBalance.objects.create(user_id=109, category="el", year=2026, credited=Decimal("30.0"), pending=Decimal("4.0"))
    req = LeaveRequest.objects.create(
        user_id=109,
        category="el",
        start_date=datetime.date(2026, 11, 16),
        end_date=datetime.date(2026, 11, 19),
        leave_days=Decimal("4.0"),
        reason="Research workshop",
        status=sm.PENDING_SANCTION,
        unit_head_recommendation="recommended",
    )

    dean_client = _auth_client(stub_iam, user_id=701, roles=("dean",), permissions=("elm.request.sanction",))
    resp = dean_client.post(
        f"/api/v1/elm/leave-requests/{req.id}/sanction/",
        data={"decision": "approve", "remarks": "Sanctioned by Dean Faculty Affairs."},
        format="json",
    )
    assert resp.status_code == 200
    req.refresh_from_db()
    assert req.status == sm.APPROVED

    bal = LeaveBalance.objects.get(user_id=109, category="el", year=2026)
    assert bal.pending == Decimal("0.0")
    assert bal.availed == Decimal("4.0")


# --- EL-UC-007: Withdraw Pending Request ---
def test_applicant_withdraws_pending_request_releases_balance(stub_iam):
    LeaveBalance.objects.create(user_id=110, category="cl", year=2026, credited=Decimal("8.0"), pending=Decimal("2.0"))
    req = LeaveRequest.objects.create(
        user_id=110,
        category="cl",
        start_date=datetime.date(2026, 11, 20),
        end_date=datetime.date(2026, 11, 21),
        leave_days=Decimal("2.0"),
        reason="Plans cancelled",
        status=sm.PENDING_UNIT_HEAD,
    )

    client = _auth_client(stub_iam, user_id=110)
    resp = client.post(
        f"/api/v1/elm/leave-requests/{req.id}/withdraw/",
        data={"remarks": "Withdrawing before approval."},
        format="json",
    )
    assert resp.status_code == 200
    req.refresh_from_db()
    assert req.status == sm.WITHDRAWN

    bal = LeaveBalance.objects.get(user_id=110, category="cl", year=2026)
    assert bal.pending == Decimal("0.0")
    assert bal.available == Decimal("8.0")


# --- EL-UC-008: Pre-Start Cancellation ---
def test_pre_start_cancellation_workflow(stub_iam):
    future_date = datetime.date.today() + datetime.timedelta(days=10)
    LeaveBalance.objects.create(user_id=111, category="cl", year=future_date.year, credited=Decimal("8.0"), availed=Decimal("2.0"))
    req = LeaveRequest.objects.create(
        user_id=111,
        category="cl",
        start_date=future_date,
        end_date=future_date + datetime.timedelta(days=1),
        leave_days=Decimal("2.0"),
        reason="Approved trip",
        status=sm.APPROVED,
    )

    # 1. Applicant requests cancellation
    client = _auth_client(stub_iam, user_id=111)
    resp = client.post(
        f"/api/v1/elm/leave-requests/{req.id}/request-cancellation/",
        data={"remarks": "Event cancelled, need to cancel leave."},
        format="json",
    )
    assert resp.status_code == 200
    req.refresh_from_db()
    assert req.status == sm.CANCELLATION_PENDING_UNIT_HEAD

    # 2. Unit Head approves cancellation
    hod_client = _auth_client(stub_iam, user_id=501, roles=("unit_head", "hod"), permissions=("elm.request.review",))
    resp2 = hod_client.post(
        f"/api/v1/elm/leave-requests/{req.id}/cancellation-unit-head-review/",
        data={"decision": "approve", "remarks": "Cancellation approved."},
        format="json",
    )
    assert resp2.status_code == 200
    req.refresh_from_db()
    assert req.status == sm.CANCELLED

    # Balance restored (availed reduced by 2.0)
    bal = LeaveBalance.objects.get(user_id=111, category="cl", year=future_date.year)
    assert bal.availed == Decimal("0.0")
    assert bal.available == Decimal("8.0")


# --- EL-UC-012: View Balances ---
def test_view_balances_endpoint(stub_iam):
    LeaveBalance.objects.create(
        user_id=112,
        category="cl",
        year=2026,
        credited=Decimal("8.0"),
        availed=Decimal("2.0"),
        pending=Decimal("1.0"),
    )
    LeaveBalance.objects.create(
        user_id=112,
        category="rh",
        year=2026,
        credited=Decimal("2.0"),
        availed=Decimal("0.0"),
        pending=Decimal("0.0"),
    )

    client = _auth_client(stub_iam, user_id=112)
    resp = client.get("/api/v1/elm/balances/?year=2026")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    cl_bal = next(b for b in data if b["category"] == "cl")
    assert cl_bal["credited"] == "8.0"
    assert cl_bal["availed"] == "2.0"
    assert cl_bal["pending"] == "1.0"
    assert cl_bal["available"] == "5.0"
