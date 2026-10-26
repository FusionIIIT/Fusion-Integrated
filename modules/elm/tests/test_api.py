"""API endpoint tests for Employee Leave Management.

Verifies authentication, authorization, role permissions, request validation,
and end-to-end API flows using DRF APIClient and stub_iam.
"""
from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.directory.models import UserRef
from modules.elm.domain.policy import ApplicationStatus
from modules.elm.models import LeaveApplication, LeaveBalance, LeaveType

pytestmark = pytest.mark.django_db


@pytest.fixture
def elm_setup():
    """Seed base leave types, users, and balances for API tests."""
    cl, _ = LeaveType.objects.get_or_create(
        code="CL", defaults={"name": "Casual Leave", "annual_quota": Decimal("8.0"),
                             "can_carry_forward": False, "requires_substitute": False,
                             "is_active": True}
    )
    el, _ = LeaveType.objects.get_or_create(
        code="EL", defaults={"name": "Earned Leave", "annual_quota": Decimal("30.0"),
                             "can_carry_forward": True, "requires_substitute": True,
                             "is_active": True}
    )
    UserRef.objects.get_or_create(user_id=1001, defaults={"username": "u1001",
                                  "display_name": "Applicant", "kind": "faculty"})
    UserRef.objects.get_or_create(user_id=1002, defaults={"username": "u1002",
                                  "display_name": "Substitute", "kind": "faculty"})
    UserRef.objects.get_or_create(user_id=2001, defaults={"username": "u2001",
                                  "display_name": "Approver", "kind": "faculty"})

    LeaveBalance.objects.get_or_create(
        user_id=1001, leave_type=cl, year=2026,
        defaults={"allocated": Decimal("8.0"), "used": Decimal("0.0"), "pending": Decimal("0.0")},
    )
    LeaveBalance.objects.get_or_create(
        user_id=1001, leave_type=el, year=2026,
        defaults={"allocated": Decimal("30.0"), "used": Decimal("0.0"), "pending": Decimal("0.0")},
    )
    return {"cl": cl, "el": el}


def _auth_client(stub_iam, user_id=1001, permissions=(), roles=("Employee",), kind="faculty"):
    """Helper to return an authenticated APIClient with stubbed IAM session."""
    session = make_session(
        user_id=user_id,
        modules=("leave_elm",),
        permissions=permissions,
        roles=roles,
        kind=kind,
    )
    stub_iam(session)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token fake-auth-token")
    return client


def test_anonymous_requests_are_rejected(elm_setup):
    """Anonymous requests must be rejected with 401."""
    client = APIClient()
    res = client.get("/api/v1/elm/applications")
    assert res.status_code == 401


def test_unauthorized_permission_is_rejected(stub_iam, elm_setup):
    """Authenticated user without specific permission gets 403."""
    # User has module grant but not application.view
    client = _auth_client(stub_iam, user_id=1001, permissions=())
    res = client.get("/api/v1/elm/applications")
    assert res.status_code == 403


def test_leave_application_apply_and_view(stub_iam, elm_setup):
    """Employee submits leave application and views their own list."""
    client = _auth_client(
        stub_iam,
        user_id=1001,
        permissions=("leave_elm.application.apply", "leave_elm.application.view"),
    )
    payload = {
        "leave_type_code": "CL",
        "start_date": "2026-11-01",
        "end_date": "2026-11-03",
        "reason": "Personal work",
    }
    res = client.post("/api/v1/elm/applications", payload, format="json")
    assert res.status_code == 201
    app_id = res.json()["id"]

    # View list
    res = client.get("/api/v1/elm/applications")
    assert res.status_code == 200
    apps = res.json()["results"] if "results" in res.json() else res.json()
    assert any(a["id"] == app_id for a in apps)


def test_substitute_decision_endpoint(stub_iam, elm_setup):
    """Nominated substitute accepts request via API."""
    # Create application awaiting substitute
    app = LeaveApplication.objects.create(
        user_id=1001,
        leave_type=elm_setup["el"],
        start_date=date(2026, 11, 10),
        end_date=date(2026, 11, 12),
        substitute_user_id=1002,
        substitute_status="pending",
        status=ApplicationStatus.AWAITING_SUBSTITUTE.value,
    )
    client = _auth_client(
        stub_iam,
        user_id=1002,
        permissions=("leave_elm.substitute.respond",),
    )
    res = client.post(
        f"/api/v1/elm/applications/{app.id}/substitute",
        {"decision": "accepted"},
        format="json",
    )
    assert res.status_code == 200
    assert res.json()["substitute_status"] == "accepted"


def test_leave_approval_decision_endpoint(stub_iam, elm_setup):
    """Approver reviews application and approves it."""
    app = LeaveApplication.objects.create(
        user_id=1001,
        leave_type=elm_setup["cl"],
        start_date=date(2026, 11, 15),
        end_date=date(2026, 11, 16),
        status=ApplicationStatus.AWAITING_UNIT_HEAD.value,
    )
    client = _auth_client(
        stub_iam,
        user_id=2001,
        permissions=("leave_elm.application.approve",),
        roles=("unit_head",),
    )
    res = client.post(
        f"/api/v1/elm/approvals/{app.id}/decide",
        {"decision": "approved", "remarks": "Approved by HOD"},
        format="json",
    )
    assert res.status_code == 200
    assert res.json()["status"] == ApplicationStatus.APPROVED.value


def test_cancellation_api_flow(stub_iam, elm_setup):
    """Employee requests cancellation and approver decides."""
    app = LeaveApplication.objects.create(
        user_id=1001,
        leave_type=elm_setup["cl"],
        start_date=date(2026, 12, 1),
        end_date=date(2026, 12, 2),
        status=ApplicationStatus.APPROVED.value,
    )
    # Request cancellation
    emp_client = _auth_client(
        stub_iam,
        user_id=1001,
        permissions=("leave_elm.application.cancel",),
    )
    res = emp_client.post(
        f"/api/v1/elm/applications/{app.id}/cancel",
        {"reason": "Event rescheduled"},
        format="json",
    )
    assert res.status_code == 200
    assert res.json()["cancellation_status"] == "requested"

    # Approver approves cancellation
    appr_client = _auth_client(
        stub_iam,
        user_id=2001,
        permissions=("leave_elm.cancellation.review",),
        roles=("unit_head",),
    )
    res = appr_client.post(
        f"/api/v1/elm/applications/{app.id}/cancel/decide",
        {"decision": "approved", "remarks": "Cancellation approved"},
        format="json",
    )
    assert res.status_code == 200
    assert res.json()["status"] == ApplicationStatus.CANCELLED.value


def test_duty_resumption_api_flow(stub_iam, elm_setup):
    """Employee submits duty resumption and approver reviews."""
    app = LeaveApplication.objects.create(
        user_id=1001,
        leave_type=elm_setup["el"],
        start_date=date(2026, 11, 20),
        end_date=date(2026, 11, 25),
        status=ApplicationStatus.APPROVED.value,
    )
    # Employee submits resumption
    emp_client = _auth_client(
        stub_iam,
        user_id=1001,
        permissions=("leave_elm.resumption.submit",),
    )
    res = emp_client.post(
        f"/api/v1/elm/applications/{app.id}/resumption",
        {"actual_resumption_date": "2026-11-25", "remarks": "Resumed duty on time"},
        format="json",
    )
    assert res.status_code == 200
    assert res.json()["resumption_status"] == "pending_review"

    # Approver reviews resumption
    appr_client = _auth_client(
        stub_iam,
        user_id=2001,
        permissions=("leave_elm.resumption.review",),
    )
    res = appr_client.post(
        f"/api/v1/elm/applications/{app.id}/resumption/decide",
        {"remarks": "Resumption accepted"},
        format="json",
    )
    assert res.status_code == 200
    assert res.json()["resumption_status"] == "reviewed_normal"


def test_offline_leave_recording_endpoint(stub_iam, elm_setup):
    """Establishment records offline sanctioned leave."""
    client = _auth_client(
        stub_iam,
        user_id=5001,
        permissions=("leave_elm.offline.record",),
        roles=("establishment",),
    )
    payload = {
        "user_id": 1001,
        "leave_type_code": "CL",
        "start_date": "2026-11-28",
        "end_date": "2026-11-29",
        "sanction_reference": "SANCTION-OFFLINE-999",
        "sanction_date": "2026-11-20",
        "sanction_authority_name": "Director Office",
        "reason": "Official offline sanction",
    }
    res = client.post("/api/v1/elm/offline-leaves", payload, format="json")
    assert res.status_code == 201
    assert res.json()["is_offline"] is True
    assert res.json()["status"] == ApplicationStatus.APPROVED.value


def test_rollover_execute_endpoint(stub_iam, elm_setup):
    """Authorized admin executes rollover endpoint."""
    client = _auth_client(
        stub_iam,
        user_id=5001,
        permissions=("leave_elm.rollover.execute",),
        roles=("establishment",),
    )
    res = client.post("/api/v1/elm/rollover", {"target_year": 2026}, format="json")
    assert res.status_code == 200
    assert isinstance(res.json(), list)
