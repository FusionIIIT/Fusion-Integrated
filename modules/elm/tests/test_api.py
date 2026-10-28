from datetime import date, timedelta

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.elm.models import (
    EmployeeProfile,
    Holiday,
    HolidayCalendar,
    LeavePolicy,
    LeaveRequest,
    OrgUnit,
    VacationPeriod,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def client_for(stub_iam):
    def make_client(user_id, permissions, *, kind="staff", modules=("employee_leave",)):
        stub_iam(make_session(
            user_id=user_id, kind=kind, modules=modules,
            permissions=permissions, roles=(kind,), active_role=kind))
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION="Token test-token")
        return client
    return make_client


@pytest.fixture
def employee():
    unit = OrgUnit.objects.create(
        code="science", name="Science", unit_head_user_id=200)
    EmployeeProfile.objects.create(
        user_id=100, employee_kind="staff", unit=unit)
    EmployeeProfile.objects.create(
        user_id=200, employee_kind="staff", unit=unit)
    LeavePolicy.objects.create(year=date.today().year)


def test_employee_can_submit_and_list_only_own_requests(client_for, employee):
    client = client_for(100, (
        "employee_leave.request.create",
        "employee_leave.request.view_self",
    ))
    starts = date.today() + timedelta(days=14)
    response = client.post("/api/v1/elm/requests/create", {
        "category": "CL",
        "starts_on": starts.isoformat(),
        "ends_on": starts.isoformat(),
        "purpose": "Personal leave",
    }, format="json")
    assert response.status_code == 201

    LeaveRequest.objects.create(
        applicant_user_id=999, category="CL", starts_on=starts, ends_on=starts,
        requested_days=1, purpose="Another employee")
    rows = client.get("/api/v1/elm/requests").json()["results"]
    assert [row["applicant_user_id"] for row in rows] == [100]


def test_employee_without_module_grant_cannot_access_elm(client_for):
    client = client_for(
        100, ("employee_leave.request.view_self",), modules=())
    response = client.get("/api/v1/elm/requests")
    assert response.status_code == 403


def test_applicant_cannot_see_another_employees_request(client_for, employee):
    starts = date.today() + timedelta(days=14)
    other = LeaveRequest.objects.create(
        applicant_user_id=999, category="CL", starts_on=starts,
        ends_on=starts, requested_days=1, purpose="Private")
    client = client_for(100, ("employee_leave.request.view_self",))
    assert client.get(f"/api/v1/elm/requests/{other.pk}").status_code == 404


def test_unassigned_user_cannot_decide_task(client_for, employee):
    from modules.elm.models import WorkflowTask

    starts = date.today() + timedelta(days=14)
    request = LeaveRequest.objects.create(
        applicant_user_id=100, category="CL", starts_on=starts,
        ends_on=starts, requested_days=1, purpose="Personal")
    task = WorkflowTask.objects.create(
        request=request, sequence=1, role="unit_head", assigned_user_id=200)
    client = client_for(300, ("employee_leave.task.decide",))
    response = client.post(
        f"/api/v1/elm/requests/{request.pk}/tasks/{task.pk}/decide",
        {"action": "approve"}, format="json")
    assert response.status_code == 404


def test_elm_urls_are_mounted():
    from django.urls import resolve

    assert resolve("/api/v1/elm/balances").url_name == "elm-my-balances"


def test_employee_cannot_create_leave_without_configured_policy(client_for, employee):
    LeavePolicy.objects.all().delete()
    client = client_for(100, (
        "employee_leave.request.create",
        "employee_leave.request.view_self",
    ))
    starts = date.today() + timedelta(days=14)
    response = client.post("/api/v1/elm/requests/create", {
        "category": "CL",
        "starts_on": starts.isoformat(),
        "ends_on": starts.isoformat(),
        "purpose": "Personal leave",
    }, format="json")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "leave_policy_missing"


def test_calendar_manager_can_publish_one_effective_calendar(client_for):
    client = client_for(900, ("employee_leave.calendar.manage",))
    year = date.today().year
    first = HolidayCalendar.objects.create(year=year, name="Initial calendar")
    replacement = HolidayCalendar.objects.create(year=year, name="Revised calendar")
    response = client.post(f"/api/v1/elm/calendars/{first.pk}/publish", {}, format="json")
    assert response.status_code == 200
    assert response.json()["status"] == "published"

    response = client.post(
        f"/api/v1/elm/calendars/{replacement.pk}/publish", {}, format="json")
    assert response.status_code == 200
    first.refresh_from_db()
    assert first.status == "superseded"
    assert response.json()["status"] == "published"


def test_calendar_manager_cannot_add_holiday_after_publication(client_for):
    calendar = HolidayCalendar.objects.create(
        year=date.today().year, name="Published", status="published")
    client = client_for(900, ("employee_leave.calendar.manage",))
    response = client.post(
        f"/api/v1/elm/calendars/{calendar.pk}/holidays",
        {"date": date.today().isoformat(), "name": "Holiday", "kind": "closed"},
        format="json")
    assert response.status_code == 404
    assert Holiday.objects.count() == 0


def test_policy_manager_must_set_positive_sla_thresholds(client_for):
    client = client_for(900, ("employee_leave.policy.manage",))
    response = client.post("/api/v1/elm/policies", {
        "year": date.today().year,
        "casual_days": "8",
        "restricted_holiday_days": "2",
        "special_casual_days": "15",
        "earned_days": "30",
        "commuted_days": "20",
        "vacation_days": "60",
        "reminder_after_hours": 0,
        "escalate_after_hours": 96,
    }, format="json")
    assert response.status_code == 400
    assert not LeavePolicy.objects.filter(year=date.today().year).exists()


def test_offline_leave_entry_requires_processor_permission(client_for):
    client = client_for(900, ("employee_leave.request.view_self",))
    response = client.post("/api/v1/elm/requests/offline", {}, format="json")
    assert response.status_code == 403


def test_processor_can_sync_offline_leave_without_starting_approval(client_for, employee):
    today = date.today()
    workdays = [
        today - timedelta(days=offset)
        for offset in range(1, 15)
        if (today - timedelta(days=offset)).weekday() < 5
    ][:2]
    client = client_for(900, ("employee_leave.request.process",))
    response = client.post("/api/v1/elm/requests/offline", {
        "applicant_user_id": 100,
        "category": "CL",
        "starts_on": min(workdays).isoformat(),
        "ends_on": max(workdays).isoformat(),
        "purpose": "Already sanctioned",
        "offline_reference": "ORDER-API-001",
        "offline_reason": "Approved system outage",
        "offline_sanctioned_on": (today - timedelta(days=10)).isoformat(),
    }, format="json")
    assert response.status_code == 201
    assert response.json()["status"] == "approved"
    assert response.json()["offline_reference"] == "ORDER-API-001"
    assert response.json()["tasks"] == []


def test_employee_can_download_only_their_own_safe_csv_application(client_for, employee):
    starts = date.today() + timedelta(days=14)
    request = LeaveRequest.objects.create(
        applicant_user_id=100, category="CL", starts_on=starts,
        ends_on=starts, requested_days=1, purpose="=1+1")
    other = LeaveRequest.objects.create(
        applicant_user_id=999, category="CL", starts_on=starts,
        ends_on=starts, requested_days=1, purpose="Private")
    client = client_for(100, ("employee_leave.request.view_self",))

    response = client.get(f"/api/v1/elm/requests/{request.pk}/export")
    content = b"".join(response.streaming_content)
    assert response.status_code == 200
    assert response["Content-Type"].startswith("text/csv")
    assert b"'=1+1" in content
    assert client.get(f"/api/v1/elm/requests/{other.pk}/export").status_code == 404


def test_calendar_manager_can_configure_vacation_periods(client_for):
    client = client_for(900, ("employee_leave.calendar.manage",))
    response = client.post("/api/v1/elm/vacation-periods", {
        "academic_year": "2026-27",
        "label": "Winter vacation",
        "starts_on": "2026-12-20",
        "ends_on": "2027-01-05",
        "source": "Academic Calendar",
    }, format="json")
    assert response.status_code == 201
    assert VacationPeriod.objects.get().label == "Winter vacation"

    invalid = client.post("/api/v1/elm/vacation-periods", {
        "academic_year": "2026-27",
        "label": "Invalid period",
        "starts_on": "2027-01-05",
        "ends_on": "2026-12-20",
        "source": "Academic Calendar",
    }, format="json")
    assert invalid.status_code == 400
    assert VacationPeriod.objects.count() == 1
