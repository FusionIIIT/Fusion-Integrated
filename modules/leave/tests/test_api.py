"""End-to-end checks for the employee and approver leave workflows."""
import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.directory.models import UserRef
from modules.leave.models import LeaveRequest

pytestmark = pytest.mark.django_db


def client_for(stub_iam, user_id, permissions):
    stub_iam(make_session(user_id=user_id, kind="staff", permissions=permissions))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token abc")
    return client


def request_for(user_id, **overrides):
    values = {
        "employee_user_id": user_id,
        "leave_type": "CL",
        "start_date": "2026-11-02",
        "end_date": "2026-11-04",
        "reason": "Personal travel",
    }
    values.update(overrides)
    return values


def employee(user_id):
    return UserRef.objects.create(user_id=user_id, username=f"staff-{user_id}",
                                  display_name="Test Employee", kind="staff", is_active=True)


def test_employee_can_submit_and_list_own_request(stub_iam):
    employee(101)
    client = client_for(stub_iam, 101, ("leave.request.create", "leave.request.view_self"))
    created = client.post("/api/v1/leave/requests", request_for(999), format="json")
    assert created.status_code == 201
    assert created.json()["employee_user_id"] == 101
    assert created.json()["status"] == "pending"
    assert client.get("/api/v1/leave/requests").json()[0]["id"] == created.json()["id"]


def test_employee_cannot_create_reversed_or_overlapping_dates(stub_iam):
    employee(101)
    client = client_for(stub_iam, 101, ("leave.request.create",))
    reversed_dates = client.post("/api/v1/leave/requests", request_for(
        101, start_date="2026-11-05", end_date="2026-11-04"), format="json")
    assert reversed_dates.status_code == 400

    LeaveRequest.objects.create(**request_for(
        101, start_date="2026-11-03", end_date="2026-11-06"))
    overlapping = client.post("/api/v1/leave/requests", request_for(101), format="json")
    assert overlapping.status_code == 400


def test_employee_can_cancel_only_own_pending_request(stub_iam):
    employee(101)
    own = LeaveRequest.objects.create(**request_for(101))
    other = LeaveRequest.objects.create(**request_for(202))
    client = client_for(stub_iam, 101, ("leave.request.delete",))
    assert client.delete(f"/api/v1/leave/requests/{own.pk}").status_code == 204
    own.refresh_from_db()
    assert own.status == "withdrawn"
    assert client.delete(f"/api/v1/leave/requests/{other.pk}").status_code == 404
    other.refresh_from_db()
    assert other.status == "pending"


def test_approver_can_decide_pending_request(stub_iam):
    leave = LeaveRequest.objects.create(**request_for(101))
    client = client_for(stub_iam, 7, ("leave.request.approve",))
    response = client.patch(f"/api/v1/leave/approvals/{leave.pk}", {
        "status": "approved", "reviewer_comment": "Enjoy your leave."
    }, format="json")
    assert response.status_code == 200
    leave.refresh_from_db()
    assert leave.status == "approved"
    assert leave.reviewed_by_user_id == 7


def test_approver_cannot_change_a_final_decision(stub_iam):
    leave = LeaveRequest.objects.create(**request_for(101), status="rejected")
    client = client_for(stub_iam, 7, ("leave.request.approve",))
    response = client.patch(f"/api/v1/leave/approvals/{leave.pk}", {
        "status": "approved"
    }, format="json")
    assert response.status_code == 404


def test_single_stage_approval_cannot_decide_higher_sanction_leave(stub_iam):
    leave = LeaveRequest.objects.create(**request_for(101, leave_type="EL"))
    client = client_for(stub_iam, 7, ("leave.request.approve",))
    response = client.patch(f"/api/v1/leave/approvals/{leave.pk}", {
        "status": "approved"
    }, format="json")
    assert response.status_code == 409
    leave.refresh_from_db()
    assert leave.status == "pending"


def test_employee_must_have_active_faculty_or_staff_projection(stub_iam):
    client = client_for(stub_iam, 999, ("leave.request.create",))
    response = client.post("/api/v1/leave/requests", request_for(999), format="json")
    assert response.status_code == 400


def test_different_cl_halves_on_one_date_do_not_overlap():
    employee(101)
    LeaveRequest.objects.create(**request_for(
        101, start_date="2026-11-02", end_date="2026-11-02", cl_period="first_half"))
    second_half = LeaveRequest(employee_user_id=101, leave_type="CL",
                               start_date="2026-11-02", end_date="2026-11-02",
                               reason="Afternoon appointment", cl_period="second_half")
    second_half.full_clean()


def test_station_leave_details_are_required_when_selected():
    employee(101)
    client = client_for(stub_iam, 101, ("leave.request.create",))
    response = client.post("/api/v1/leave/requests", request_for(
        101, leave_type="EL", station_leave=True), format="json")
    assert response.status_code == 400
