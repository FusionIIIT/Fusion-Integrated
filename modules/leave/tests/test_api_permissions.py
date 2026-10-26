"""API authorization and identity scoping for ELM."""
from datetime import date

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.leave.models import (
    HolidayCalendar,
    LeaveAccount,
    LeaveHierarchyConfig,
    LeavePolicyConfig,
    LeaveRequest,
)
from modules.leave.services.leave_services import effective_holiday_dates

pytestmark = pytest.mark.django_db


def _client(stub_iam, permissions=(), modules=("leave",), uid=1001, department="CSE",
            kind="faculty", active_role="faculty"):
    stub_iam(make_session(
        user_id=uid,
        permissions=permissions,
        modules=modules,
        kind=kind,
        roles=(active_role,),
        active_role=active_role,
        department=department,
    ))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token abc")
    return client


@pytest.fixture
def leave_rows():
    for uid, day in ((1001, 1), (1002, 8)):
        LeaveAccount.objects.create(
            user_id=str(uid), category="CL", year=2026, balance=8.0
        )
        LeaveRequest.objects.create(
            applicant_id=str(uid),
            applicant_role="faculty",
            category="CL",
            start_date=date(2026, 4, day),
            end_date=date(2026, 4, day),
            purpose="Test leave",
        )


def test_module_grant_is_required_even_with_permission(stub_iam):
    client = _client(
        stub_iam,
        permissions=("leave.request.view_self",),
        modules=(),
    )
    assert client.get("/api/v1/leave/accounts/").status_code == 403


def test_request_list_get_requires_view_self(stub_iam):
    client = _client(stub_iam, permissions=("leave.request.create",))
    assert client.get("/api/v1/leave/requests/").status_code == 403


def test_request_list_post_requires_create(stub_iam):
    client = _client(stub_iam, permissions=("leave.request.view_self",))
    assert client.post("/api/v1/leave/requests/", {}, format="json").status_code == 403


def test_own_lists_ignore_spoofed_user_header(stub_iam, leave_rows):
    client = _client(stub_iam, permissions=("leave.request.view_self",))
    client.credentials(
        HTTP_AUTHORIZATION="Token abc",
        HTTP_X_USER_ID="1002",
    )
    accounts = client.get("/api/v1/leave/accounts/").json()
    requests = client.get("/api/v1/leave/requests/").json()
    assert [row["user_id"] for row in accounts] == ["1001"]
    assert [row["applicant_id"] for row in requests] == ["1001"]


@pytest.mark.parametrize(
    ("path", "payload", "wrong_permission"),
    [
        ("/api/v1/leave/requests/1/substitute-action/", {}, "leave.request.review"),
        ("/api/v1/leave/requests/1/unit-head-action/", {}, "leave.request.assign"),
        ("/api/v1/leave/requests/1/establishment-route/", {}, "leave.request.approve"),
        ("/api/v1/leave/requests/1/sanction-decision/", {}, "leave.request.review"),
        ("/api/v1/leave/requests/1/withdraw/", {}, "leave.request.approve"),
        (
            "/api/v1/leave/requests/1/resumption/",
            {"action": "SUBMIT"},
            "leave.resumption.review",
        ),
        (
            "/api/v1/leave/requests/1/resumption/",
            {"action": "REVIEW"},
            "leave.resumption.create",
        ),
        (
            "/api/v1/leave/requests/1/resumption/",
            {"action": "INVALID"},
            "leave.resumption.create",
        ),
    ],
)
def test_workflow_actions_require_their_own_permission(
    stub_iam, path, payload, wrong_permission
):
    client = _client(stub_iam, permissions=(wrong_permission,))
    response = client.post(path, payload, format="json")
    assert response.status_code == 403


def test_self_permission_can_read_own_accounts(stub_iam, leave_rows):
    client = _client(stub_iam, permissions=("leave.request.view_self",))
    assert client.get("/api/v1/leave/accounts/").status_code == 200


@pytest.mark.parametrize(
    ("path", "permission"),
    [
        ("/api/v1/leave/requests/inbox/", "leave.request.view"),
        ("/api/v1/leave/admin/policy/", "leave.policy.manage"),
        ("/api/v1/leave/admin/hierarchy/", "leave.policy.manage"),
        ("/api/v1/leave/admin/calendar/", "leave.calendar.publish"),
        ("/api/v1/leave/admin/offline-sync/", "leave.record.manage"),
        ("/api/v1/leave/requests/1/record/", "leave.record.manage"),
    ],
)
def test_new_capabilities_require_their_declared_permission(stub_iam, path, permission):
    client = _client(stub_iam, permissions=("leave.request.view_self",))
    assert client.get(path).status_code == 403


def test_inbox_only_returns_tasks_assigned_to_authenticated_actor(stub_iam):
    route = LeaveHierarchyConfig.objects.create(
        department="CSE", applicant_role="faculty", category="EL", unit_head_id="1001"
    )
    LeaveRequest.objects.create(
        applicant_id="other", applicant_role="faculty", category="EL",
        start_date=date(2026, 4, 1), end_date=date(2026, 4, 2), purpose="assigned",
        status="AWAITING_UNIT_HEAD", unit_head_id="1001", routing_config=route,
    )
    LeaveRequest.objects.create(
        applicant_id="other-2", applicant_role="faculty", category="EL",
        start_date=date(2026, 4, 3), end_date=date(2026, 4, 4), purpose="not assigned",
        status="AWAITING_UNIT_HEAD", unit_head_id="1002",
    )
    LeaveRequest.objects.create(
        applicant_id="legacy", applicant_role="faculty", category="EL",
        start_date=date(2026, 4, 5), end_date=date(2026, 4, 6), purpose="legacy spoof",
        status="AWAITING_UNIT_HEAD", unit_head_id="1001",
    )
    client = _client(stub_iam, permissions=("leave.request.view",))
    response = client.get("/api/v1/leave/requests/inbox/")
    assert response.status_code == 200
    assert [row["purpose"] for row in response.json()] == ["assigned"]


def test_leave_application_uses_configured_route_and_ignores_supplied_route_ids(stub_iam):
    LeaveHierarchyConfig.objects.create(
        department="CSE", applicant_role="faculty", category="CL",
        unit_head_id="trusted-hod",
    )
    client = _client(stub_iam, permissions=("leave.request.create",))
    response = client.post("/api/v1/leave/requests/", {
        "category": "CL", "start_date": "2026-04-06", "end_date": "2026-04-06",
        "purpose": "route test", "unit_head_id": "attacker",
        "sanctioning_authority_id": "attacker",
    }, format="json")
    assert response.status_code == 201, response.json()
    saved = LeaveRequest.objects.get(pk=response.json()["id"])
    assert saved.unit_head_id == "trusted-hod"
    assert saved.sanctioning_authority_id == ""


def test_policy_and_hierarchy_admin_endpoints_save_current_configuration(stub_iam):
    client = _client(stub_iam, permissions=("leave.policy.manage",))
    policy = client.put("/api/v1/leave/admin/policy/CL/", {
        "annual_entitlement": 12, "allows_half_day": True,
    }, format="json")
    assert policy.status_code == 200
    assert LeavePolicyConfig.objects.get(category="CL").annual_entitlement == 12

    route = client.put("/api/v1/leave/admin/hierarchy/", {
        "department": "CSE", "applicant_role": "faculty", "category": "CL",
        "unit_head_id": "hod-2",
    }, format="json")
    assert route.status_code == 200
    assert LeaveHierarchyConfig.objects.get(
        department="CSE", applicant_role="faculty", category="CL"
    ).unit_head_id == "hod-2"
    sla = client.put("/api/v1/leave/admin/sla/UNIT_HEAD_REVIEW/", {
        "reminder_hours": 18, "escalation_hours": 36,
    }, format="json")
    assert sla.status_code == 200
    assert sla.json()["reminder_hours"] == 18


def test_calendar_admin_stages_then_publishes_replacement(stub_iam):
    old_date = date(2026, 1, 1)
    new_date = date(2026, 1, 2)
    HolidayCalendar.objects.create(date=old_date, title="Current", is_published=True)
    client = _client(stub_iam, permissions=("leave.calendar.publish",))
    staged = client.post("/api/v1/leave/admin/calendar/", {
        "name": "Replacement", "entries": [{
            "date": new_date.isoformat(), "title": "RH", "is_restricted_holiday": True,
        }],
    }, format="json")
    assert staged.status_code == 201
    assert effective_holiday_dates() == {old_date}
    revised = client.put(f"/api/v1/leave/admin/calendar/{staged.json()['id']}/", {
        "name": "Replacement revised", "entries": [{
            "date": "2026-01-03", "title": "Revised RH", "is_restricted_holiday": True,
        }],
    }, format="json")
    assert revised.status_code == 200
    new_date = date(2026, 1, 3)
    assert effective_holiday_dates() == {old_date}

    published = client.post(
        f"/api/v1/leave/admin/calendar/{staged.json()['id']}/publish/", {}, format="json"
    )
    assert published.status_code == 200
    assert effective_holiday_dates() == {new_date}


def test_offline_sync_and_record_correction_api(stub_iam):
    unauthorized = _client(stub_iam, permissions=("leave.record.manage",),
                           kind="operator", active_role="deputy_registrar")
    denied = unauthorized.post("/api/v1/leave/admin/offline-sync/", {}, format="json")
    assert denied.status_code == 403
    LeaveAccount.objects.create(
        user_id="employee-2", employee_type="staff", category="CL", year=2026, balance=8,
    )
    client = _client(stub_iam, permissions=("leave.record.manage",),
                     kind="operator", active_role="leave_administrator")
    created = client.post("/api/v1/leave/admin/offline-sync/", {
        "applicant_id": "employee-2", "employee_type": "staff", "category": "CL",
        "start_date": "2026-04-06", "end_date": "2026-04-06",
        "reference_evidence": "paper-ref-2", "unavailable_reason": "ELM outage",
    }, format="json")
    assert created.status_code == 201, created.json()
    req_id = created.json()["id"]
    saved = LeaveRequest.objects.get(pk=req_id)
    assert saved.status == "APPROVED" and saved.is_offline_sync

    corrected = client.patch(
        f"/api/v1/leave/requests/{req_id}/record/",
        {"purpose": "Corrected description", "reason": "transcription correction"},
        format="json",
    )
    assert corrected.status_code == 200
    saved.refresh_from_db()
    assert saved.purpose == "Corrected description"
    assert saved.status == "APPROVED"
