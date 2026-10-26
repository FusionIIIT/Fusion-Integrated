# API endpoint integration tests for ELM
from datetime import date, timedelta
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.leave.domain.constants import (
    HALF_DAY_FIRST,
    HALF_DAY_NONE,
    LEAVE_TYPE_CL,
    LEAVE_TYPE_EL,
    STATUS_APPROVED,
    STATUS_PENDING,
)
from modules.leave.models import LeaveApplication, LeaveBalance

pytestmark = pytest.mark.django_db


def _make_client(stub_iam, user_id=1001, permissions=(), roles=("faculty",), kind="faculty"):
    session = make_session(
        user_id=user_id,
        permissions=permissions,
        modules=("leave_elm",),
        roles=roles,
        kind=kind,
        active_role=roles[0] if roles else "faculty",
    )
    stub_iam(session)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token mock-token-123")
    return client


def test_leave_balances_endpoint(stub_iam):
    """GET /api/v1/leave/balances returns initialized balances with available count."""
    client = _make_client(stub_iam, user_id=2001, permissions=("leave_elm.application.view",))
    resp = client.get("/api/v1/leave/balances")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 6
    cl_bal = next(b for b in data if b["leave_type"] == "CL")
    assert cl_bal["allocated"] == "8.00"
    assert cl_bal["available"] == "8.00"


def test_leave_application_create_endpoint(stub_iam):
    """POST /api/v1/leave/applications computes days and creates application."""
    client = _make_client(
        stub_iam,
        user_id=2002,
        permissions=("leave_elm.application.view", "leave_elm.application.apply"),
    )
    payload = {
        "leave_type": "CL",
        "start_date": "2026-11-04",
        "end_date": "2026-11-04",
        "half_day": "FIRST_HALF",
        "reason": "Personal urgency",
    }
    resp = client.post("/api/v1/leave/applications", payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "PENDING"
    assert data["days"] == "0.50"
    assert data["user_id"] == 2002


def test_student_prohibited_from_applying(stub_iam):
    """BR-EL-036: Students are prohibited from applying for employee leave."""
    client = _make_client(
        stub_iam,
        user_id=3001,
        permissions=("leave_elm.application.view", "leave_elm.application.apply"),
        roles=("student",),
        kind="student",
    )
    payload = {
        "leave_type": "CL",
        "start_date": "2026-11-04",
        "end_date": "2026-11-04",
        "half_day": "NONE",
        "reason": "Family function",
    }
    resp = client.post("/api/v1/leave/applications", payload)
    assert resp.status_code == 403
    assert "Students are not eligible" in str(resp.json())


def test_review_application_endpoint(stub_iam):
    """Approver can approve application and deduct balance."""
    app = LeaveApplication.objects.create(
        user_id=4001,
        leave_type=LEAVE_TYPE_CL,
        start_date=date(2026, 11, 4),
        end_date=date(2026, 11, 4),
        half_day=HALF_DAY_FIRST,
        days=Decimal("0.50"),
        reason="Dentist appointment",
        status=STATUS_PENDING,
    )
    LeaveBalance.objects.create(
        user_id=4001,
        leave_type=LEAVE_TYPE_CL,
        year=2026,
        allocated=Decimal("8.00"),
        used=Decimal("0.00"),
    )

    approver_client = _make_client(
        stub_iam,
        user_id=9001,
        permissions=("leave_elm.application.view", "leave_elm.application.approve"),
        roles=("HOD",),
        kind="faculty",
    )
    resp = approver_client.post(
        f"/api/v1/leave/applications/{app.id}/review",
        {"action": "APPROVE", "remarks": "Sanctioned"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "APPROVED"


def test_self_approval_blocked_in_api(stub_iam):
    """Approver attempting to review their own application is forbidden."""
    app = LeaveApplication.objects.create(
        user_id=5001,
        leave_type=LEAVE_TYPE_CL,
        start_date=date(2026, 11, 4),
        end_date=date(2026, 11, 4),
        half_day=HALF_DAY_NONE,
        days=Decimal("1.00"),
        reason="Travel",
        status=STATUS_PENDING,
    )
    approver_client = _make_client(
        stub_iam,
        user_id=5001,
        permissions=("leave_elm.application.view", "leave_elm.application.approve"),
    )
    resp = approver_client.post(
        f"/api/v1/leave/applications/{app.id}/review",
        {"action": "APPROVE"},
    )
    assert resp.status_code == 403


def test_withdraw_endpoint(stub_iam):
    """Applicant can withdraw pending leave."""
    app = LeaveApplication.objects.create(
        user_id=6001,
        leave_type=LEAVE_TYPE_CL,
        start_date=date(2026, 11, 4),
        end_date=date(2026, 11, 4),
        half_day=HALF_DAY_NONE,
        days=Decimal("1.00"),
        reason="Family event",
        status=STATUS_PENDING,
    )
    client = _make_client(
        stub_iam,
        user_id=6001,
        permissions=("leave_elm.application.view", "leave_elm.application.withdraw"),
    )
    resp = client.post(f"/api/v1/leave/applications/{app.id}/withdraw")
    assert resp.status_code == 200
    assert resp.json()["status"] == "WITHDRAWN"


def test_cancel_endpoint(stub_iam):
    """Applicant can cancel approved leave before start date."""
    future_start = date.today() + timedelta(days=15)
    app = LeaveApplication.objects.create(
        user_id=7001,
        leave_type=LEAVE_TYPE_EL,
        start_date=future_start,
        end_date=future_start + timedelta(days=2),
        half_day=HALF_DAY_NONE,
        days=Decimal("3.00"),
        reason="Holiday trip",
        status=STATUS_APPROVED,
    )
    LeaveBalance.objects.create(
        user_id=7001,
        leave_type=LEAVE_TYPE_EL,
        year=future_start.year,
        allocated=Decimal("30.00"),
        used=Decimal("3.00"),
    )

    client = _make_client(
        stub_iam,
        user_id=7001,
        permissions=("leave_elm.application.view", "leave_elm.application.cancel"),
    )
    resp = client.post(f"/api/v1/leave/applications/{app.id}/cancel")
    assert resp.status_code == 200
    assert resp.json()["status"] == "CANCELLED"
