"""Tests for leave API endpoints."""
from datetime import date

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.leave.models import (
    LeaveApplication,
    LeaveApplicationTransition,
    LeaveBalance,
    LeaveCategory,
)

pytestmark = pytest.mark.django_db


def _client(stub_iam, **kw):
    defaults = {
        "user_id": 1,
        "modules": ("leave_management",),
        "permissions": (
            "leave_management.application.view_self",
            "leave_management.application.create",
            "leave_management.application.view",
            "leave_management.application.review",
            "leave_management.application.delete",
            "leave_management.application.respond",
            "leave_management.balance.view",
        ),
    }
    defaults.update(kw)
    stub_iam(make_session(**defaults))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token test-token")
    return c


def test_categories_endpoint(stub_iam):
    LeaveCategory.objects.create(code="CL", name="Casual Leave")
    c = _client(stub_iam)
    response = c.get("/api/v1/leave/categories")
    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_balances_endpoint_scopes_to_own(stub_iam):
    cl = LeaveCategory.objects.create(code="CL", name="Casual Leave")

    # User 1 balance
    LeaveBalance.objects.create(user_id=1, category=cl, year=2026, balance_days=8.0)
    # User 2 balance
    LeaveBalance.objects.create(user_id=2, category=cl, year=2026, balance_days=8.0)

    # Client authenticated as user 1 (only view_self permission)
    c = _client(stub_iam, user_id=1, permissions=("leave_management.application.view_self",))
    response = c.get("/api/v1/leave/balances")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["user_id"] == 1


def test_apply_endpoint_success(stub_iam):
    cl = LeaveCategory.objects.create(code="CL", name="Casual Leave")

    # Setup user 1 balance
    LeaveBalance.objects.create(user_id=1, category=cl, year=2026, balance_days=8.0)

    c = _client(stub_iam, user_id=1)
    payload = {
        "category_code": "CL",
        "start_date": "2026-11-02",
        "end_date": "2026-11-03",
        "reason": "Personal work"
    }
    response = c.post("/api/v1/leave/applications/apply", data=payload)

    assert response.status_code == 201
    assert response.json()["status"] == "awaiting_unit_head"


def test_apply_endpoint_invalid_dates(stub_iam):
    cl = LeaveCategory.objects.create(code="CL", name="Casual Leave")
    LeaveBalance.objects.create(user_id=1, category=cl, year=2026, balance_days=8.0)

    c = _client(stub_iam, user_id=1)
    payload = {
        "category_code": "CL",
        "start_date": "2026-11-03",
        "end_date": "2026-11-02",
        "reason": "Invalid dates"
    }
    response = c.post("/api/v1/leave/applications/apply", data=payload)

    assert response.status_code == 409


def test_applications_list_and_detail(stub_iam):
    cl = LeaveCategory.objects.create(code="CL", name="Casual Leave")
    LeaveBalance.objects.create(user_id=1, category=cl, year=2026, balance_days=8.0)
    LeaveBalance.objects.create(user_id=2, category=cl, year=2026, balance_days=8.0)

    # Create applications
    app1 = LeaveApplication.objects.create(user_id=1, category=cl, start_date=date(2026, 11, 2), end_date=date(2026, 11, 3), reason="Work 1", status="awaiting_unit_head")
    app2 = LeaveApplication.objects.create(user_id=2, category=cl, start_date=date(2026, 11, 2), end_date=date(2026, 11, 3), reason="Work 2", status="awaiting_unit_head")

    # Test list (User 1 sees only own)
    c1 = _client(stub_iam, user_id=1, permissions=("leave_management.application.view_self",))
    resp_list = c1.get("/api/v1/leave/applications")
    assert resp_list.status_code == 200
    assert len(resp_list.json()) == 1
    assert resp_list.json()[0]["id"] == app1.id

    # Test detail (User 1 views own)
    resp_detail_own = c1.get(f"/api/v1/leave/applications/{app1.id}")
    assert resp_detail_own.status_code == 200

    # Test detail (User 1 tries to view User 2's)
    resp_detail_other = c1.get(f"/api/v1/leave/applications/{app2.id}")
    assert resp_detail_other.status_code == 404


def test_transition_endpoint_approve(stub_iam):
    cl = LeaveCategory.objects.create(code="CL", name="Casual Leave")
    LeaveBalance.objects.create(user_id=1, category=cl, year=2026, balance_days=8.0)

    # Create application in initial state
    app = LeaveApplication.objects.create(user_id=1, category=cl, start_date=date(2026, 11, 2), end_date=date(2026, 11, 3), reason="Personal", status="awaiting_unit_head")

    # Client authenticated as reviewer (user_id=2)
    c = _client(stub_iam, user_id=2, permissions=("leave_management.application.review", "leave_management.application.view"))
    payload = {
        "to_status": "approved",
        "reason": "Approved by HOD"
    }
    response = c.post(f"/api/v1/leave/applications/{app.id}/transition", data=payload)

    assert response.status_code == 200
    assert response.json()["status"] == "approved"


def test_application_history(stub_iam):
    cl = LeaveCategory.objects.create(code="CL", name="Casual Leave")
    LeaveBalance.objects.create(user_id=1, category=cl, year=2026, balance_days=8.0)

    # Create application and transition it
    app = LeaveApplication.objects.create(user_id=1, category=cl, start_date=date(2026, 11, 2), end_date=date(2026, 11, 3), reason="Personal", status="approved")

    # Transition it (using a reviewer user_id=2)
    LeaveApplicationTransition.objects.create(application=app, from_status="awaiting_unit_head", to_status="approved", actor_user_id=2, reason="Approved")

    # Client as user 1 views history
    c1 = _client(stub_iam, user_id=1, permissions=("leave_management.application.view_self",))
    response = c1.get(f"/api/v1/leave/applications/{app.id}/history")

    assert response.status_code == 200
    assert len(response.json()) >= 1


def test_unauthenticated_request_rejected(stub_iam):
    # Client without credentials
    c = APIClient()
    response = c.get("/api/v1/leave/categories")

    assert response.status_code == 401
