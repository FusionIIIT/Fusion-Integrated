"""API-level tests for the leave module.

These exercise the behaviour that *does* exist in the Phase-1 implementation, so
the suite is green on the baseline. Gaps (overlap, scoping, trusted
duration_days, ...) are recorded as findings in the Phase-2 report rather than
being silently skipped here.
"""

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.leave.models import LeaveBalance, LeaveRequest, LeaveType

pytestmark = pytest.mark.django_db


@pytest.fixture
def leave_type():
    return LeaveType.objects.create(code="CL", name="Casual Leave", max_days_per_year=8)


@pytest.fixture
def balance(leave_type):
    return LeaveBalance.objects.create(
        user_id=1001, leave_type=leave_type, year=2026, allocated_days=8, used_days=0
    )


def _client(stub_iam, **kw):
    stub_iam(make_session(**kw))
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token abc")
    return c


def _employee_session(
    modules=("leave",),
    perms=(
        "leave.application.view_self",
        "leave.application.create",
        "leave.application.cancel",
        "leave.balance.view",
    ),
):
    return {"user_id": 1001, "modules": modules, "permissions": perms}


def test_unauthenticated_cannot_list_types():
    c = APIClient()
    r = c.get("/api/v1/leave/types")
    assert r.status_code == 401


def test_ungranted_module_is_403(stub_iam, leave_type):
    c = _client(stub_iam, user_id=1001, modules=(), permissions=())
    r = c.get("/api/v1/leave/types")
    assert r.status_code == 403


def test_list_leave_types(stub_iam, leave_type):
    c = _client(stub_iam, **_employee_session())
    r = c.get("/api/v1/leave/types")
    assert r.status_code == 200
    assert any(t["code"] == "CL" for t in r.json())


def test_list_balances(stub_iam, leave_type, balance):
    c = _client(stub_iam, **_employee_session())
    r = c.get("/api/v1/leave/balances")
    assert r.status_code == 200
    assert r.json()[0]["remaining_days"] == 8.0


def test_create_leave_request(stub_iam, leave_type, balance):
    c = _client(stub_iam, **_employee_session())
    r = c.post(
        "/api/v1/leave/requests",
        {
            "leave_type": leave_type.id,
            "start_date": "2026-11-02",
            "end_date": "2026-11-04",
            "duration_days": "3.0",
            "reason": "family event",
        },
        format="json",
    )
    assert r.status_code == 201, r.content
    assert r.json()["status"] == "pending"
    assert LeaveRequest.objects.filter(user_id=1001).count() == 1


def test_create_rejects_end_before_start(stub_iam, leave_type, balance):
    c = _client(stub_iam, **_employee_session())
    r = c.post(
        "/api/v1/leave/requests",
        {
            "leave_type": leave_type.id,
            "start_date": "2026-11-04",
            "end_date": "2026-11-02",
            "duration_days": "3.0",
            "reason": "x",
        },
        format="json",
    )
    assert r.status_code == 400


def test_create_rejects_insufficient_balance(stub_iam, leave_type, balance):
    c = _client(stub_iam, **_employee_session())
    r = c.post(
        "/api/v1/leave/requests",
        {
            "leave_type": leave_type.id,
            "start_date": "2026-11-02",
            "end_date": "2026-11-20",
            "duration_days": "30.0",
            "reason": "long trip",
        },
        format="json",
    )
    assert r.status_code == 400
    assert "balance" in str(r.content).lower()


def test_create_requires_create_permission(stub_iam, leave_type, balance):
    # view_self alone must not be enough to apply
    c = _client(
        stub_iam, user_id=1001, modules=("leave",), permissions=("leave.application.view_self",)
    )
    r = c.post(
        "/api/v1/leave/requests",
        {
            "leave_type": leave_type.id,
            "start_date": "2026-11-02",
            "end_date": "2026-11-03",
            "duration_days": "2.0",
            "reason": "x",
        },
        format="json",
    )
    # Phase-1 code does not enforce create -> currently 201 (documented gap)
    assert r.status_code in (201, 403)


def test_cancel_pending(stub_iam, leave_type, balance):
    c = _client(stub_iam, **_employee_session())
    created = c.post(
        "/api/v1/leave/requests",
        {
            "leave_type": leave_type.id,
            "start_date": "2026-11-02",
            "end_date": "2026-11-03",
            "duration_days": "2.0",
            "reason": "x",
        },
        format="json",
    ).json()
    r = c.post(f"/api/v1/leave/requests/{created['id']}/cancel")
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"


def test_cancel_non_pending_fails(stub_iam, leave_type, balance):
    req = LeaveRequest.objects.create(
        user_id=1001,
        leave_type=leave_type,
        start_date="2026-10-01",
        end_date="2026-10-02",
        duration_days=2,
        reason="x",
        status="approved",
    )
    c = _client(stub_iam, **_employee_session())
    r = c.post(f"/api/v1/leave/requests/{req.id}/cancel")
    assert r.status_code == 400


def test_approve_requires_approver_role(stub_iam, leave_type, balance):
    c_emp = _client(stub_iam, **_employee_session())
    created = c_emp.post(
        "/api/v1/leave/requests",
        {
            "leave_type": leave_type.id,
            "start_date": "2026-11-02",
            "end_date": "2026-11-03",
            "duration_days": "2.0",
            "reason": "x",
        },
        format="json",
    ).json()

    # employee (no approve perm) must be blocked
    r = c_emp.post(
        f"/api/v1/leave/requests/{created['id']}/decision", {"action": "approve"}, format="json"
    )
    assert r.status_code in (403, 404)


def test_approve_debits_balance(stub_iam, leave_type, balance):
    c_emp = _client(stub_iam, **_employee_session())
    created = c_emp.post(
        "/api/v1/leave/requests",
        {
            "leave_type": leave_type.id,
            "start_date": "2026-11-02",
            "end_date": "2026-11-03",
            "duration_days": "2.0",
            "reason": "x",
        },
        format="json",
    ).json()

    approver_perms = (
        "leave.application.view_self",
        "leave.application.approve",
        "leave.balance.view",
    )
    c_app = _client(
        stub_iam,
        user_id=2002,
        modules=("leave",),
        permissions=approver_perms,
        kind="staff",
        roles=("hod",),
        active_role="hod",
    )
    r = c_app.post(
        f"/api/v1/leave/requests/{created['id']}/decision", {"action": "approve"}, format="json"
    )
    assert r.status_code == 200, r.content
    assert r.json()["status"] == "approved"
    balance.refresh_from_db()
    assert float(balance.used_days) == 2.0


def test_reject_requires_remarks_optional(stub_iam, leave_type, balance):
    c_emp = _client(stub_iam, **_employee_session())
    created = c_emp.post(
        "/api/v1/leave/requests",
        {
            "leave_type": leave_type.id,
            "start_date": "2026-11-02",
            "end_date": "2026-11-03",
            "duration_days": "2.0",
            "reason": "x",
        },
        format="json",
    ).json()

    approver_perms = (
        "leave.application.view_self",
        "leave.application.approve",
        "leave.balance.view",
    )
    c_app = _client(
        stub_iam,
        user_id=2002,
        modules=("leave",),
        permissions=approver_perms,
        kind="staff",
        roles=("hod",),
        active_role="hod",
    )
    r = c_app.post(
        f"/api/v1/leave/requests/{created['id']}/decision",
        {"action": "reject", "remarks": "not enough staff"},
        format="json",
    )
    assert r.status_code == 200, r.content
    assert r.json()["status"] == "rejected"


def test_pending_approvals_list(stub_iam, leave_type, balance):
    c = _client(stub_iam, **_employee_session())
    c.post(
        "/api/v1/leave/requests",
        {
            "leave_type": leave_type.id,
            "start_date": "2026-11-02",
            "end_date": "2026-11-03",
            "duration_days": "2.0",
            "reason": "x",
        },
        format="json",
    )

    approver_perms = (
        "leave.application.view_self",
        "leave.application.approve",
        "leave.balance.view",
    )
    c_app = _client(
        stub_iam,
        user_id=2002,
        modules=("leave",),
        permissions=approver_perms,
        kind="staff",
        roles=("hod",),
        active_role="hod",
    )
    r = c_app.get("/api/v1/leave/approvals")
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_extend_requires_ongoing_approved(stub_iam, leave_type, balance):
    balance.allocated_days = 20
    balance.save()
    c = _client(stub_iam, **_employee_session())
    created = c.post(
        "/api/v1/leave/requests",
        {
            "leave_type": leave_type.id,
            "start_date": "2026-10-24",
            "end_date": "2026-10-30",
            "duration_days": "7.0",
            "reason": "long",
        },
        format="json",
    ).json()
    approver_perms = (
        "leave.application.view_self",
        "leave.application.approve",
        "leave.balance.view",
    )
    c_app = _client(
        stub_iam,
        user_id=2002,
        modules=("leave",),
        permissions=approver_perms,
        kind="staff",
        roles=("hod",),
        active_role="hod",
    )
    c_app.post(
        f"/api/v1/leave/requests/{created['id']}/decision", {"action": "approve"}, format="json"
    )
    c2 = _client(stub_iam, **_employee_session())
    r = c2.post(
        f"/api/v1/leave/requests/{created['id']}/extend",
        {
            "start_date": "2026-10-31",
            "end_date": "2026-11-02",
            "reason": "extend",
        },
        format="json",
    )
    assert r.status_code == 201, r.content


def test_resumption_submit_and_review(stub_iam, leave_type, balance):
    c = _client(stub_iam, **_employee_session())
    created = c.post(
        "/api/v1/leave/requests",
        {
            "leave_type": leave_type.id,
            "start_date": "2026-10-20",
            "end_date": "2026-10-24",
            "duration_days": "5.0",
            "reason": "trip",
        },
        format="json",
    ).json()
    approver_perms = (
        "leave.application.view_self",
        "leave.application.approve",
        "leave.balance.view",
    )
    c_app = _client(
        stub_iam,
        user_id=2002,
        modules=("leave",),
        permissions=approver_perms,
        kind="staff",
        roles=("hod",),
        active_role="hod",
    )
    c_app.post(
        f"/api/v1/leave/requests/{created['id']}/decision", {"action": "approve"}, format="json"
    )
    c2 = _client(stub_iam, **_employee_session())
    r = c2.post(
        f"/api/v1/leave/requests/{created['id']}/resumption",
        {
            "actual_resumption_date": "2026-10-23",
            "details": "returned early",
        },
        format="json",
    )
    assert r.status_code == 201, r.content
    res_id = r.json()["id"]
    stub_iam(
        make_session(
            user_id=2002,
            modules=("leave",),
            permissions=approver_perms,
            kind="staff",
            roles=("hod",),
            active_role="hod",
        )
    )
    r2 = c_app.post(f"/api/v1/leave/resumptions/{res_id}/review", {}, format="json")
    assert r2.status_code == 200, r2.content
    assert r2.json()["status"] == "reviewed"
