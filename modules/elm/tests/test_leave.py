import datetime

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.elm.models import LeaveBalance, LeaveType

pytestmark = pytest.mark.django_db

def _client(stub_iam, user_id, *perms):
    stub_iam(make_session(user_id=user_id, kind="faculty", modules=("leave_elm",), permissions=perms))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c

@pytest.fixture
def leave_type():
    return LeaveType.objects.create(code="CL", name="Casual Leave", max_days_per_year=8)

@pytest.fixture
def balance(leave_type):
    d0 = datetime.date.today() + datetime.timedelta(days=30)
    return LeaveBalance.objects.create(employee_id=1001, leave_type=leave_type, year=d0.year, allotted=8, used=0)

def test_apply_counts_days_inclusive(stub_iam, balance):
    c = _client(stub_iam, 1001, "leave_elm.application.apply")
    d0 = datetime.date.today() + datetime.timedelta(days=30)
    d2 = d0 + datetime.timedelta(days=2)
    response = c.post("/api/v1/elm/applications", {
        "leave_type": balance.leave_type.id,
        "start_date": d0.isoformat(),
        "end_date": d2.isoformat(),
        "reason": "Vacation"
    }, format="json")
    assert response.status_code == 201
    assert response.json()["days"] == 3
    assert response.json()["status"] == "SUBMITTED"

def test_overlap_is_rejected(stub_iam, balance):
    c = _client(stub_iam, 1001, "leave_elm.application.apply")
    d0 = datetime.date.today() + datetime.timedelta(days=30)
    d1 = d0 + datetime.timedelta(days=1)
    d2 = d0 + datetime.timedelta(days=2)
    c.post("/api/v1/elm/applications", {
        "leave_type": balance.leave_type.id,
        "start_date": d0.isoformat(),
        "end_date": d2.isoformat(),
        "reason": "Vacation"
    }, format="json")
    response = c.post("/api/v1/elm/applications", {
        "leave_type": balance.leave_type.id,
        "start_date": d1.isoformat(),
        "end_date": d2.isoformat(),
        "reason": "Vacation"
    }, format="json")
    assert response.status_code == 409

def test_insufficient_balance_is_rejected(stub_iam, balance):
    c = _client(stub_iam, 1001, "leave_elm.application.apply")
    d0 = datetime.date.today() + datetime.timedelta(days=30)
    d2 = d0 + datetime.timedelta(days=2)
    response = c.post("/api/v1/elm/applications", {
        "leave_type": balance.leave_type.id,
        "start_date": d0.isoformat(),
        "end_date": d2.isoformat(),
        "reason": "Vacation"
    }, format="json")
    assert response.status_code == 201
    response = c.post("/api/v1/elm/applications", {
        "leave_type": balance.leave_type.id,
        "start_date": d0.isoformat(),
        "end_date": d2.isoformat(),
        "reason": "Vacation"
    }, format="json")
    assert response.status_code == 409

def test_end_before_start_is_rejected(stub_iam, balance):
    c = _client(stub_iam, 1001, "leave_elm.application.apply")
    d0 = datetime.date.today() + datetime.timedelta(days=30)
    d1 = d0 + datetime.timedelta(days=1)
    response = c.post("/api/v1/elm/applications", {
        "leave_type": balance.leave_type.id,
        "start_date": d1.isoformat(),
        "end_date": d0.isoformat(),
        "reason": "Vacation"
    }, format="json")
    assert response.status_code == 400

def test_apply_needs_apply_permission(stub_iam, balance):
    c = _client(stub_iam, 1001, "leave_elm.policy.manage")
    response = c.post("/api/v1/elm/applications", {
        "leave_type": balance.leave_type.id,
        "start_date": "2023-10-01",
        "end_date": "2023-10-03",
        "reason": "Vacation"
    }, format="json")
    assert response.status_code == 403

def _apply(stub_iam, balance, user_id=1001, *extra_perms, days=3):
    """Apply as the applicant for `days` days starting 30 days from now; return the new id."""
    c = _client(stub_iam, user_id, "leave_elm.application.apply", *extra_perms)
    d0 = datetime.date.today() + datetime.timedelta(days=30)
    response = c.post("/api/v1/elm/applications", {
        "leave_type": balance.leave_type.id,
        "start_date": d0.isoformat(),
        "end_date": (d0 + datetime.timedelta(days=days - 1)).isoformat(),
        "reason": "Vacation"
    }, format="json")
    assert response.status_code == 201
    return c, response.json()["id"]

def _approver(stub_iam):
    return _client(stub_iam, 2002, "leave_elm.application.approve")

def test_approve_uses_balance(stub_iam, balance):
    _, app_id = _apply(stub_iam, balance)
    response = _approver(stub_iam).post(f"/api/v1/elm/applications/{app_id}/decide", {
        "approve": True,
        "remarks": ""
    }, format="json")
    assert response.status_code == 200
    assert response.json()["status"] == "APPROVED"
    balance.refresh_from_db()
    assert balance.used == 3

def test_approver_cannot_approve_own_application(stub_iam, balance):
    c, app_id = _apply(stub_iam, balance, 1001, "leave_elm.application.approve")
    response = c.post(f"/api/v1/elm/applications/{app_id}/decide", {
        "approve": True,
        "remarks": ""
    }, format="json")
    assert response.status_code == 403

def test_decide_twice_is_conflict(stub_iam, balance):
    _, app_id = _apply(stub_iam, balance)
    c = _approver(stub_iam)
    response = c.post(f"/api/v1/elm/applications/{app_id}/decide", {
        "approve": True,
        "remarks": ""
    }, format="json")
    assert response.status_code == 200
    response = c.post(f"/api/v1/elm/applications/{app_id}/decide", {
        "approve": True,
        "remarks": ""
    }, format="json")
    assert response.status_code == 409

def test_unknown_application_is_404(stub_iam, balance):
    c = _client(stub_iam, 2002, "leave_elm.application.approve")
    response = c.post("/api/v1/elm/applications/999999/decide", {
        "approve": True,
        "remarks": ""
    }, format="json")
    assert response.status_code == 404

def test_withdraw_pending(stub_iam, balance):
    _, app_id = _apply(stub_iam, balance)
    c2 = _client(stub_iam, 3003, "leave_elm.application.apply")
    response = c2.post(f"/api/v1/elm/applications/{app_id}/withdraw", format="json")
    assert response.status_code == 403
    c = _client(stub_iam, 1001, "leave_elm.application.apply")
    response = c.post(f"/api/v1/elm/applications/{app_id}/withdraw", format="json")
    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"

def test_cancel_approved_restores_balance(stub_iam, balance):
    _, app_id = _apply(stub_iam, balance)
    response = _approver(stub_iam).post(f"/api/v1/elm/applications/{app_id}/decide", {
        "approve": True,
        "remarks": ""
    }, format="json")
    assert response.status_code == 200
    c = _client(stub_iam, 1001, "leave_elm.application.apply")
    response = c.post(f"/api/v1/elm/applications/{app_id}/cancel", format="json")
    assert response.status_code == 200
    assert response.json()["status"] == "CANCELLED"
    balance.refresh_from_db()
    assert balance.used == 0

def test_no_edit_endpoint(stub_iam, balance):
    c, app_id = _apply(stub_iam, balance)
    response = c.put(f"/api/v1/elm/applications/{app_id}", {
        "status": "CANCELLED"
    }, format="json")
    assert response.status_code in (404, 405)
    response = c.patch(f"/api/v1/elm/applications/{app_id}", {
        "status": "CANCELLED"
    }, format="json")
    assert response.status_code in (404, 405)

def test_balance_lists_available(stub_iam, balance):
    c = _client(stub_iam, 1001, "leave_elm.application.apply", "leave_elm.balance.view")
    response = c.get("/api/v1/elm/balance")
    assert response.status_code == 200
    assert response.json()[0]["available"] == 8

def test_admin_creates_leave_type_and_employee_cannot(stub_iam, balance):
    c = _client(stub_iam, 4004, "leave_elm.policy.manage")
    response = c.post("/api/v1/elm/admin/types", {
        "code": "SL",
        "name": "Sick Leave",
        "max_days_per_year": 10,
        "requires_document": False,
        "is_active": True
    }, format="json")
    assert response.status_code == 201
    c2 = _client(stub_iam, 1001, "leave_elm.application.apply")
    response = c2.post("/api/v1/elm/admin/types", {
        "code": "SL",
        "name": "Sick Leave",
        "max_days_per_year": 10,
        "requires_document": False,
        "is_active": True
    }, format="json")
    assert response.status_code == 403

def test_allotment_above_leave_type_max_is_rejected(stub_iam, balance):
    c = _client(stub_iam, 4004, "leave_elm.policy.manage")
    response = c.post("/api/v1/elm/admin/balances", {
        "employee_id": 1001,
        "leave_type_id": balance.leave_type.id,
        "year": balance.year,
        "allotted": balance.leave_type.max_days_per_year + 1,
    }, format="json")
    assert response.status_code == 400
    balance.refresh_from_db()
    assert balance.allotted == 8
