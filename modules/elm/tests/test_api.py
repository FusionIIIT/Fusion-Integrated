from datetime import date
from decimal import Decimal
import pytest
from rest_framework.test import APIClient

from conftest import make_session
from fusion_auth.client import UserRef
from modules.elm.models import (
    LeaveAuthorityRule,
    LeaveCalendar,
    LeavePolicy,
    LeaveRequest,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def test_setup(db):
    LeavePolicy.objects.update_or_create(
        leave_type_code="CL",
        defaults={
            "employee_kinds": ["staff", "faculty"],
            "annual_entitlement": Decimal("8"),
            "annual_entitlement_by_kind": {"staff": "8.00", "faculty": "8.00"},
            "day_counting": "WORKING_DAYS",
            "half_day_allowed": True,
            "carries_forward": False,
            "is_active": True,
        },
    )
    calendar, _ = LeaveCalendar.objects.get_or_create(
        kind="HOLIDAY",
        year=2026,
        revision=1,
        defaults={
            "label": "2026 Test Calendar",
            "status": "PUBLISHED",
            "effective_from": date(2026, 1, 1),
            "effective_through": date(2026, 12, 31),
            "working_weekdays": [0, 1, 2, 3, 4],
        },
    )
    rule, _ = LeaveAuthorityRule.objects.get_or_create(
        department="Engineering",
        leave_type_code="CL",
        step_order=1,
        defaults={
            "stage": "UNIT_HEAD",
            "decision_mode": "FINAL",
            "approver_user_id": 9001,
            "is_active": True,
        },
    )
    return calendar, rule


def _client(stub_iam, user_id=1001, kind="staff", permissions=(), active_role="staff", roles=("staff",)):
    session = make_session(
        user_id=user_id,
        kind=kind,
        modules=("leave",),
        permissions=permissions,
        active_role=active_role,
        roles=roles,
    )
    stub_iam(
        session,
        users={
            user_id: UserRef(
                user_id=user_id,
                username=f"u{user_id}",
                display_name=f"User {user_id}",
                kind=kind,
                department="Engineering",
            ),
            5001: UserRef(
                user_id=5001,
                username="u5001",
                display_name="Substitute 5001",
                kind=kind,
                department="Engineering",
            ),
            9001: UserRef(
                user_id=9001,
                username="u9001",
                display_name="Unit Head 9001",
                kind=kind,
                department="Engineering",
            ),
        },
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token fake-token")
    return c


def test_employee_can_view_balances(stub_iam, test_setup):
    client = _client(stub_iam, user_id=1001, permissions=("leave.request.view_self",))
    res = client.get("/api/v1/leave/balances")
    assert res.status_code == 200
    data = res.json()["results"]
    assert any(b["leave_type_code"] == "CL" for b in data)


def test_employee_can_submit_and_view_leave_request(stub_iam, test_setup):
    client = _client(
        stub_iam,
        user_id=1001,
        permissions=("leave.request.create", "leave.request.view_self"),
    )
    payload = {
        "leave_type_code": "CL",
        "requested_start_date": "2026-10-26",
        "requested_end_date": "2026-10-26",
        "day_part": "FULL",
        "substitute_user_id": 5001,
    }
    submit_res = client.post("/api/v1/leave/requests/submit", payload, format="json")
    assert submit_res.status_code == 201
    req_id = submit_res.json()["id"]
    assert submit_res.json()["status"] == "PENDING_SUBSTITUTE"

    my_res = client.get("/api/v1/leave/requests")
    assert my_res.status_code == 200
    ids = [r["id"] for r in my_res.json()["results"]]
    assert req_id in ids


def test_substitute_can_respond_and_approver_can_decide(stub_iam, test_setup):
    # 1. Employee submits
    emp_client = _client(
        stub_iam,
        user_id=1001,
        permissions=("leave.request.create", "leave.request.view_self"),
    )
    payload = {
        "leave_type_code": "CL",
        "requested_start_date": "2026-10-26",
        "requested_end_date": "2026-10-26",
        "day_part": "FULL",
        "substitute_user_id": 5001,
    }
    submit_res = emp_client.post("/api/v1/leave/requests/submit", payload, format="json")
    req_id = submit_res.json()["id"]

    # 2. Substitute views tasks and accepts
    sub_client = _client(
        stub_iam,
        user_id=5001,
        permissions=("leave.substitute.respond",),
    )
    tasks_res = sub_client.get("/api/v1/leave/substitutions")
    assert tasks_res.status_code == 200
    assert any(t["id"] == req_id for t in tasks_res.json()["results"])

    resp_res = sub_client.post(
        f"/api/v1/leave/requests/{req_id}/substitute-response",
        {"action": "ACCEPT"},
        format="json",
    )
    assert resp_res.status_code == 200
    assert resp_res.json()["status"] == "PENDING_UNIT_HEAD"

    # 3. Approver views approvals and approves
    app_client = _client(
        stub_iam,
        user_id=9001,
        permissions=("leave.request.approve",),
        active_role="unit_head",
    )
    apps_res = app_client.get("/api/v1/leave/approvals")
    assert apps_res.status_code == 200
    assert any(a["request"]["id"] == req_id for a in apps_res.json()["results"])

    dec_res = app_client.post(
        f"/api/v1/leave/requests/{req_id}/decision",
        {"action": "APPROVE", "reason": "All good"},
        format="json",
    )
    assert dec_res.status_code == 200
    assert dec_res.json()["status"] == "APPROVED"


def test_employee_can_withdraw_pending_request(stub_iam, test_setup):
    emp_client = _client(
        stub_iam,
        user_id=1001,
        permissions=("leave.request.create", "leave.request.delete"),
    )
    payload = {
        "leave_type_code": "CL",
        "requested_start_date": "2026-10-26",
        "requested_end_date": "2026-10-26",
        "day_part": "FULL",
        "substitute_user_id": 5001,
    }
    submit_res = emp_client.post("/api/v1/leave/requests/submit", payload, format="json")
    req_id = submit_res.json()["id"]

    withdraw_res = emp_client.post(f"/api/v1/leave/requests/{req_id}/withdraw")
    assert withdraw_res.status_code == 200
    assert withdraw_res.json()["status"] == "WITHDRAWN"


def test_permission_denied_without_proper_grants(stub_iam, test_setup):
    unauth_client = _client(stub_iam, user_id=1001, permissions=())
    res = unauth_client.get("/api/v1/leave/balances")
    assert res.status_code == 403
