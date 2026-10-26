"""API tests for Employee Leave Management endpoints and permissions."""
from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.leave.models import (
    LeaveApplication,
    LeaveType,
)
from modules.leave.services import get_or_create_balance

pytestmark = pytest.mark.django_db


@pytest.fixture
def leave_types(db):
    cl = LeaveType.objects.create(
        code="CL",
        name="Casual Leave",
        max_days_per_year=Decimal("8.0"),
        requires_substitute=True,
    )
    el = LeaveType.objects.create(
        code="EL",
        name="Earned Leave",
        max_days_per_year=Decimal("30.0"),
        requires_substitute=True,
        is_continuous_counting=True,
    )
    return {"CL": cl, "EL": el}


def _auth_client(stub_iam, user_id=1001, permissions=None, roles=None):
    perms = permissions or ("leave.application.view", "leave.application.apply")
    session = make_session(
        user_id=user_id,
        permissions=perms,
        modules=("leave",),
        roles=roles or ("faculty",),
    )
    stub_iam(session)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token fake-token")
    return client


def test_leave_types_list(stub_iam, leave_types):
    client = _auth_client(stub_iam)
    resp = client.get("/api/v1/leave/types/")
    assert resp.status_code == 200
    assert len(resp.json()) >= 2


def test_leave_balances_list(stub_iam, leave_types):
    client = _auth_client(stub_iam, user_id=1001)
    resp = client.get("/api/v1/leave/balances/")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 2


def test_apply_for_leave_api(stub_iam, leave_types):
    client = _auth_client(stub_iam, user_id=1001)
    payload = {
        "leave_type": leave_types["CL"].id,
        "start_date": "2026-11-02",
        "end_date": "2026-11-03",
        "reason": "Personal work",
        "substitute_id": "u2002",
    }
    resp = client.post("/api/v1/leave/applications/", payload, format="json")
    assert resp.status_code == 201
    assert resp.json()["status"] == LeaveApplication.STATUS_AWAITING_SUBSTITUTE


def test_substitute_response_api(stub_iam, leave_types):
    cl = leave_types["CL"]
    app = LeaveApplication.objects.create(
        applicant_id="u1001",
        leave_type=cl,
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 2),
        reason="Test",
        substitute_id="u2002",
        status=LeaveApplication.STATUS_AWAITING_SUBSTITUTE,
        substitute_status=LeaveApplication.SUB_STATUS_PENDING,
    )

    client = _auth_client(stub_iam, user_id=2002)
    resp = client.post(
        f"/api/v1/leave/applications/{app.id}/substitute/",
        {"response": "accept", "remarks": "Covering duties"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == LeaveApplication.STATUS_AWAITING_UNIT_HEAD


def test_leave_review_approval_api(stub_iam, leave_types):
    cl = leave_types["CL"]
    app = LeaveApplication.objects.create(
        applicant_id="u1001",
        leave_type=cl,
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 2),
        reason="Test",
        status=LeaveApplication.STATUS_AWAITING_UNIT_HEAD,
    )
    get_or_create_balance("u1001", cl, 2026)

    client = _auth_client(
        stub_iam,
        user_id=9001,
        permissions=("leave.application.view", "leave.application.approve"),
    )
    resp = client.post(
        f"/api/v1/leave/applications/{app.id}/review/",
        {"review_action": "approve", "remarks": "Approved by HOD"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == LeaveApplication.STATUS_APPROVED


def test_leave_withdraw_api(stub_iam, leave_types):
    cl = leave_types["CL"]
    app = LeaveApplication.objects.create(
        applicant_id="u1001",
        leave_type=cl,
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 2),
        reason="Test",
        status=LeaveApplication.STATUS_AWAITING_UNIT_HEAD,
    )

    client = _auth_client(stub_iam, user_id=1001)
    resp = client.post(
        f"/api/v1/leave/applications/{app.id}/withdraw/",
        {"remarks": "No longer needed"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == LeaveApplication.STATUS_WITHDRAWN


def test_unauthorized_access_denied(stub_iam):
    client = APIClient()
    resp = client.get("/api/v1/leave/types/")
    assert resp.status_code in (401, 403)
