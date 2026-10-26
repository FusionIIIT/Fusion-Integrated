"""End-to-end checks for the employee and approver leave workflows."""
import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.directory.models import UserRef
from modules.leave.models import LeaveBalance, LeaveRequest

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


def employee(user_id, department="Engineering"):
    return UserRef.objects.create(user_id=user_id, username=f"staff-{user_id}",
                                  display_name="Test Employee", kind="staff",
                                  department=department, is_active=True)


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
    employee(101)
    employee(7)
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
    employee(7)
    leave = LeaveRequest.objects.create(**request_for(101), status="rejected")
    client = client_for(stub_iam, 7, ("leave.request.approve",))
    response = client.patch(f"/api/v1/leave/approvals/{leave.pk}", {
        "status": "approved"
    }, format="json")
    assert response.status_code == 404


def test_single_stage_approval_cannot_decide_higher_sanction_leave(stub_iam):
    employee(7)
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


def test_faculty_and_staff_leave_categories_are_enforced(stub_iam):
    employee(101)
    client = client_for(stub_iam, 101, ("leave.request.create",))
    response = client.post("/api/v1/leave/requests", request_for(
        101, leave_type="VL"), format="json")
    assert response.status_code == 400


def test_pending_requests_reserve_balance(stub_iam):
    employee(101)
    client = client_for(stub_iam, 101, ("leave.request.create",))
    first = client.post("/api/v1/leave/requests", request_for(
        101, start_date="2026-11-02", end_date="2026-11-06"), format="json")
    assert first.status_code == 201
    assert first.json()["chargeable_days"] == "5.00"
    second = client.post("/api/v1/leave/requests", request_for(
        101, start_date="2026-11-09", end_date="2026-11-12"), format="json")
    assert second.status_code == 400


def test_restricted_holiday_requires_current_published_calendar(stub_iam):
    employee(101)
    client = client_for(stub_iam, 101, ("leave.request.create",))
    body = request_for(101, leave_type="RH", start_date="2026-11-02",
                       end_date="2026-11-02")
    assert client.post("/api/v1/leave/requests", body, format="json").status_code == 400

    admin = client_for(stub_iam, 7, ("leave.calendar.manage", "leave.calendar.publish"))
    draft = admin.post("/api/v1/leave/admin/calendars", {
        "title": "2026 holidays", "days": [{"date": "2026-11-02",
            "is_closed": True, "is_restricted_holiday": True}]
    }, format="json")
    assert draft.status_code == 201
    published = admin.post(f"/api/v1/leave/admin/calendars/{draft.json()['id']}/publish")
    assert published.status_code == 200
    client = client_for(stub_iam, 101, ("leave.request.create",))
    assert client.post("/api/v1/leave/requests", body, format="json").status_code == 201


def test_approval_deducts_balance_and_records_audit(stub_iam):
    employee(101)
    employee(7)
    leave = LeaveRequest.objects.create(**request_for(
        101, start_date="2026-11-02", end_date="2026-11-04",
        chargeable_days="3.00", charge_by_year={"2026": "3.00"}))
    client = client_for(stub_iam, 7, ("leave.request.approve",))
    response = client.patch(f"/api/v1/leave/approvals/{leave.pk}", {
        "status": "approved"
    }, format="json")
    assert response.status_code == 200
    account = LeaveBalance.objects.get(employee_user_id=101, leave_type="CL", year=2026)
    assert account.available == 5
    assert account.changes.get().amount == -3


def test_unit_head_cannot_decide_for_another_department(stub_iam):
    employee(101, department="Engineering")
    employee(7, department="Finance")
    leave = LeaveRequest.objects.create(**request_for(101))
    client = client_for(stub_iam, 7, ("leave.request.approve",))
    response = client.patch(f"/api/v1/leave/approvals/{leave.pk}", {
        "status": "approved"
    }, format="json")
    assert response.status_code == 404


def test_admin_balance_adjustment_is_audited(stub_iam):
    employee(101)
    admin = client_for(stub_iam, 7, ("leave.balance.update",))
    response = admin.post("/api/v1/leave/admin/balances", {
        "employee_user_id": 101, "leave_type": "CL", "year": 2026,
        "amount": "-2.00", "note": "Correct an offline-approved leave",
    }, format="json")
    assert response.status_code == 200
    balance = LeaveBalance.objects.get(employee_user_id=101, leave_type="CL", year=2026)
    assert balance.available == 6
    assert balance.changes.get().action == "adjustment"


def test_different_cl_halves_on_one_date_do_not_overlap():
    employee(101)
    LeaveRequest.objects.create(**request_for(
        101, start_date="2026-11-02", end_date="2026-11-02", cl_period="first_half"))
    second_half = LeaveRequest(employee_user_id=101, leave_type="CL",
                               start_date="2026-11-02", end_date="2026-11-02",
                               reason="Afternoon appointment", cl_period="second_half")
    second_half.full_clean()


def test_employee_can_submit_both_cl_halves_on_the_same_date(stub_iam):
    employee(101)
    client = client_for(stub_iam, 101, ("leave.request.create",))
    first = client.post("/api/v1/leave/requests", request_for(
        101, start_date="2026-11-02", end_date="2026-11-02",
        cl_period="first_half"), format="json")
    second = client.post("/api/v1/leave/requests", request_for(
        101, start_date="2026-11-02", end_date="2026-11-02",
        cl_period="second_half"), format="json")
    assert first.status_code == second.status_code == 201
    assert first.json()["chargeable_days"] == second.json()["chargeable_days"] == "0.50"


def test_station_leave_details_are_required_when_selected():
    employee(101)
    client = client_for(stub_iam, 101, ("leave.request.create",))
    response = client.post("/api/v1/leave/requests", request_for(
        101, leave_type="EL", station_leave=True), format="json")
    assert response.status_code == 400
