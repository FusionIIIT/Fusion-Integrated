from datetime import date

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.leave.models import (
    LeaveBalance,
    LeaveManagerAssignment,
    LeaveRequest,
    LeaveType,
)

pytestmark = pytest.mark.django_db


def _client(stub_iam, *, user_id, permissions, role="staff", users=None):
    stub_iam(make_session(user_id=user_id, kind=role, modules=("leave",),
                          permissions=permissions), users=users)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token test")
    return client


@pytest.fixture
def leave_rows():
    leave_type = LeaveType.objects.create(code="annual", name="Annual")
    requests = [LeaveRequest.objects.create(
        user_id=uid, leave_type=leave_type,
        start_date=date(2026, 11, 2), end_date=date(2026, 11, 2),
        days=1, reason="Personal") for uid in (1001, 1002, 9000)]
    LeaveManagerAssignment.objects.create(manager_user_id=9000, employee_user_id=1001)
    return leave_type, requests


def test_manager_list_and_review_are_limited_to_assigned_employees(
        stub_iam, leave_rows, user_ref):
    _, (assigned, unrelated, manager_own) = leave_rows
    client = _client(stub_iam, user_id=9000,
                     permissions=("leave.request.view", "leave.request.review"),
                     users={1001: user_ref(1001, "Asha Verma")})

    listing = client.get("/api/v1/leave/requests")
    assert listing.status_code == 200
    assert [row["user_id"] for row in listing.json()["results"]] == [1001]
    assert listing.json()["results"][0]["employee_name"] == "Asha Verma"

    allowed = client.post(f"/api/v1/leave/requests/{assigned.pk}/review",
                          {"decision": "approved"}, format="json")
    denied = client.post(f"/api/v1/leave/requests/{unrelated.pk}/review",
                         {"decision": "approved"}, format="json")
    own = client.post(f"/api/v1/leave/requests/{manager_own.pk}/review",
                      {"decision": "approved"}, format="json")
    assert allowed.status_code == 200
    assert denied.status_code == 404
    assert own.status_code == 404


def test_employee_submit_cancel_then_manager_approves_end_to_end(stub_iam, user_ref):
    leave_type = LeaveType.objects.create(code="annual", name="Annual")
    LeaveBalance.objects.create(
        user_id=1001, leave_type=leave_type, year=2026,
        allocated_days="10.00", carried_days="0.00")
    LeaveManagerAssignment.objects.create(manager_user_id=9000, employee_user_id=1001)
    employee = _client(
        stub_iam, user_id=1001,
        permissions=("leave.request.view_self", "leave.request.create",
                     "leave.request.cancel"))

    first = employee.post("/api/v1/leave/requests/create", {
        "leave_type": leave_type.pk, "start_date": "2026-11-02",
        "end_date": "2026-11-02", "reason": "Personal day",
    }, format="json")
    assert first.status_code == 201
    assert first.json()["days"] == 1
    assert employee.post(
        f"/api/v1/leave/requests/{first.json()['id']}/cancel", {}).status_code == 200

    second = employee.post("/api/v1/leave/requests/create", {
        "leave_type": leave_type.pk, "start_date": "2026-11-03",
        "end_date": "2026-11-03", "reason": "Another personal day",
    }, format="json")
    assert second.status_code == 201
    assert employee.post(
        f"/api/v1/leave/requests/{second.json()['id']}/review",
        {"decision": "approved"}, format="json").status_code == 403

    manager = _client(
        stub_iam, user_id=9000,
        permissions=("leave.request.view", "leave.request.review"),
        users={1001: user_ref(1001, "Asha Verma")})
    listing = manager.get("/api/v1/leave/requests")
    assert listing.status_code == 200
    manager_rows = listing.json()["results"]
    assert len(manager_rows) == 2  # cancelled and currently pending
    assert all(item["employee_name"] == "Asha Verma" for item in manager_rows)
    approved = manager.post(
        f"/api/v1/leave/requests/{second.json()['id']}/review",
        {"decision": "approved", "note": "Approved"}, format="json")
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"

    employee = _client(
        stub_iam, user_id=1001,
        permissions=("leave.request.view_self", "leave.request.cancel"))
    assert employee.post(
        f"/api/v1/leave/requests/{second.json()['id']}/cancel", {}).status_code == 400


def test_employee_cannot_read_another_employees_request(stub_iam, leave_rows):
    _, (assigned, _, _) = leave_rows
    client = _client(stub_iam, user_id=1002,
                     permissions=("leave.request.view_self", "leave.request.cancel"))

    response = client.get("/api/v1/leave/mine")

    assert response.status_code == 200
    assert [row["user_id"] for row in response.json()["requests"]] == [1002]
    assert client.post(f"/api/v1/leave/requests/{assigned.pk}/cancel", {}).status_code == 404


def test_configuration_endpoints_require_dedicated_permission(stub_iam):
    client = _client(stub_iam, user_id=1001,
                     permissions=("leave.request.create",))
    response = client.post("/api/v1/leave/configuration/types",
                           {"code": "annual", "name": "Annual",
                            "annual_allowance": "20.00", "is_active": True},
                           format="json")
    assert response.status_code == 403


def test_admin_can_configure_type_balance_and_manager_scope(stub_iam):
    client = _client(stub_iam, user_id=1,
                     permissions=("leave.configuration.manage",), role="staff")
    leave_type = client.post(
        "/api/v1/leave/configuration/types",
        {"code": "annual", "name": "Annual", "annual_allowance": "20.00",
         "is_active": True}, format="json")
    assert leave_type.status_code == 201

    balance = client.put(
        "/api/v1/leave/configuration/balances",
        {"user_id": 1001, "leave_type": leave_type.json()["id"], "year": 2026,
         "allocated_days": "18.00", "carried_days": "2.00"}, format="json")
    assert balance.status_code == 200
    assert balance.json()["allocated_days"] == "18.00"
    assert LeaveBalance.objects.count() == 1

    assignment = client.post(
        "/api/v1/leave/configuration/manager-assignments",
        {"manager_user_id": 9000, "employee_user_id": 1001}, format="json")
    assert assignment.status_code == 201
    duplicate = client.post(
        "/api/v1/leave/configuration/manager-assignments",
        {"manager_user_id": 9000, "employee_user_id": 1001}, format="json")
    assert duplicate.status_code == 200
    assert LeaveManagerAssignment.objects.count() == 1

    removed = client.delete(
        f"/api/v1/leave/configuration/manager-assignments/{assignment.json()['id']}")
    assert removed.status_code == 204
    assert LeaveManagerAssignment.objects.count() == 0
