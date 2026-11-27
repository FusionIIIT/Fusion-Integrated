"""Integration and security tests for Employee Leave Management REST API."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from fusion_auth.client import UserRef
from modules.leave.domain.state_machine import LeaveState
from modules.leave.models import (
    LeaveBalance,
    LeaveRequest,
    LeaveType,
    SubstituteNomination,
)


@pytest.fixture
def api_env(db, stub_iam):
    users = {
        1001: UserRef(
            user_id=1001,
            username="fac_alice",
            display_name="Alice CSE",
            kind="faculty",
            department="Computer Science & Engineering",
        ),
        1002: UserRef(
            user_id=1002,
            username="fac_bob",
            display_name="Bob CSE",
            kind="faculty",
            department="Computer Science & Engineering",
        ),
        2001: UserRef(
            user_id=2001,
            username="hod_cse",
            display_name="Dr. Smith HOD CSE",
            kind="faculty",
            department="Computer Science & Engineering",
        ),
        2002: UserRef(
            user_id=2002,
            username="hod_me",
            display_name="Dr. Taylor HOD ME",
            kind="faculty",
            department="Mechanical Engineering",
        ),
        3001: UserRef(
            user_id=3001,
            username="dean_acad",
            display_name="Prof. Johnson Dean",
            kind="faculty",
            department="Administration",
        ),
        5001: UserRef(
            user_id=5001,
            username="admin_user",
            display_name="Admin Staff",
            kind="staff",
            department="Establishment",
        ),
    }
    stub_iam(users=users)

    # Leave Types
    cl = LeaveType.objects.create(
        code="CL",
        name="Casual Leave",
        allows_half_day=True,
        lapses_at_year_end=True,
        is_continuous_count=False,
    )
    el = LeaveType.objects.create(
        code="EL",
        name="Earned Leave",
        allows_half_day=False,
        carries_forward=True,
        is_continuous_count=True,
        requires_substitute=True,
        allows_extension=True,
    )

    # Balances for Alice (1001)
    LeaveBalance.objects.create(
        user_id=1001,
        leave_type=cl,
        year=2026,
        credited_days=Decimal("8.0"),
        used_days=Decimal("0.0"),
        available_days=Decimal("8.0"),
    )
    LeaveBalance.objects.create(
        user_id=1001,
        leave_type=el,
        year=2026,
        credited_days=Decimal("30.0"),
        used_days=Decimal("0.0"),
        available_days=Decimal("30.0"),
    )

    # Balances for Bob (1002)
    LeaveBalance.objects.create(
        user_id=1002,
        leave_type=cl,
        year=2026,
        credited_days=Decimal("8.0"),
        used_days=Decimal("0.0"),
        available_days=Decimal("8.0"),
    )

    return {"users": users, "cl": cl, "el": el}


def auth_as(stub_iam, api_env, user_id=1001, roles=("faculty",), permissions=None):
    if permissions is None:
        permissions = (
            "leave.request.view_self",
            "leave.request.create",
            "leave.request.delete",
        )
    client = APIClient()
    session = make_session(
        user_id=user_id,
        modules=("leave",),
        permissions=permissions,
        roles=roles,
        active_role=roles[0] if roles else "faculty",
    )
    stub_iam(session=session, users=api_env["users"])
    return client


# 1. Authentication and Permission Failures


@pytest.mark.django_db
def test_balances_forbidden_without_module_grant(api_env, stub_iam):
    client = APIClient()
    session = make_session(
        user_id=1001,
        modules=(),  # No module grant
        permissions=("leave.request.view_self",),
    )
    stub_iam(session=session, users=api_env["users"])
    res = client.get("/api/v1/leave/balances/", HTTP_AUTHORIZATION="Token tok-123")
    assert res.status_code == 403


@pytest.mark.django_db
def test_balances_forbidden_without_view_self(api_env, stub_iam):
    client = APIClient()
    session = make_session(
        user_id=1001,
        modules=("leave",),
        permissions=(),  # Missing leave.request.view_self
    )
    stub_iam(session=session, users=api_env["users"])
    res = client.get("/api/v1/leave/balances/", HTTP_AUTHORIZATION="Token tok-123")
    assert res.status_code == 403


@pytest.mark.django_db
def test_apply_forbidden_without_create_permission(api_env, stub_iam):
    client = auth_as(stub_iam, api_env, user_id=1001, permissions=("leave.request.view_self",))
    res = client.post(
        "/api/v1/leave/applications/",
        data={
            "leave_type_code": "CL",
            "start_date": "2026-10-15",
            "end_date": "2026-10-16",
            "reason": "Personal work",
        },
        HTTP_AUTHORIZATION="Token tok-123",
    )
    assert res.status_code == 403


@pytest.mark.django_db
def test_approvals_queue_forbidden_without_approve_permission(api_env, stub_iam):
    client = auth_as(stub_iam, api_env, user_id=1001)
    res = client.get("/api/v1/leave/approvals/", HTTP_AUTHORIZATION="Token tok-123")
    assert res.status_code == 403


# 2. Employee Operations & Data Isolation


@pytest.mark.django_db
def test_employee_balances_and_history(api_env, stub_iam):
    client = auth_as(stub_iam, api_env, user_id=1001)

    # Balances
    res = client.get("/api/v1/leave/balances/", HTTP_AUTHORIZATION="Token tok-123")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 2
    codes = {b["leave_type"]["code"] for b in data}
    assert codes == {"CL", "EL"}

    # Apply CL
    apply_res = client.post(
        "/api/v1/leave/applications/",
        data={
            "leave_type_code": "CL",
            "start_date": "2026-10-15",
            "end_date": "2026-10-16",
            "reason": "Family function",
        },
        HTTP_AUTHORIZATION="Token tok-123",
    )
    assert apply_res.status_code == 201
    created = apply_res.json()
    assert created["status"] == "awaiting_unit_head"
    assert created["requested_days"] == "2.0"
    req_id = created["id"]

    # History (own requests)
    hist_res = client.get("/api/v1/leave/requests/", HTTP_AUTHORIZATION="Token tok-123")
    assert hist_res.status_code == 200
    assert len(hist_res.json()) == 1
    assert hist_res.json()[0]["id"] == req_id

    # Detail view by owner
    det_res = client.get(f"/api/v1/leave/requests/{req_id}/", HTTP_AUTHORIZATION="Token tok-123")
    assert det_res.status_code == 200
    assert det_res.json()["id"] == req_id


@pytest.mark.django_db
def test_employee_data_isolation(api_env, stub_iam):
    alice_client = auth_as(stub_iam, api_env, user_id=1001)
    apply_res = alice_client.post(
        "/api/v1/leave/applications/",
        data={
            "leave_type_code": "CL",
            "start_date": "2026-10-15",
            "end_date": "2026-10-16",
            "reason": "Personal work",
        },
        HTTP_AUTHORIZATION="Token tok-123",
    )
    req_id = apply_res.json()["id"]

    # Bob attempts to view Alice's request
    bob_client = auth_as(stub_iam, api_env, user_id=1002)
    bob_det = bob_client.get(
        f"/api/v1/leave/requests/{req_id}/", HTTP_AUTHORIZATION="Token tok-123"
    )
    assert bob_det.status_code == 403

    # Bob attempts to withdraw Alice's request
    bob_withdraw = bob_client.post(
        f"/api/v1/leave/requests/{req_id}/withdraw/",
        data={"remarks": "Malicious attempt"},
        HTTP_AUTHORIZATION="Token tok-123",
    )
    assert bob_withdraw.status_code == 403

    # Bob checks his own history -> empty
    bob_hist = bob_client.get("/api/v1/leave/requests/", HTTP_AUTHORIZATION="Token tok-123")
    assert bob_hist.status_code == 200
    assert len(bob_hist.json()) == 0


@pytest.mark.django_db
def test_withdraw_success_and_conflict(api_env, stub_iam):
    alice_client = auth_as(stub_iam, api_env, user_id=1001)
    apply_res = alice_client.post(
        "/api/v1/leave/applications/",
        data={
            "leave_type_code": "CL",
            "start_date": "2026-10-15",
            "end_date": "2026-10-16",
            "reason": "Doctor appointment",
        },
        HTTP_AUTHORIZATION="Token tok-123",
    )
    req_id = apply_res.json()["id"]

    res = alice_client.post(
        f"/api/v1/leave/requests/{req_id}/withdraw/",
        data={"remarks": "No longer needed"},
        HTTP_AUTHORIZATION="Token tok-123",
    )
    assert res.status_code == 200
    assert res.json()["status"] == "withdrawn"

    res2 = alice_client.post(
        f"/api/v1/leave/requests/{req_id}/withdraw/",
        data={"remarks": "Duplicate"},
        HTTP_AUTHORIZATION="Token tok-123",
    )
    assert res2.status_code == 409


@pytest.mark.django_db
def test_invalid_application_payload(api_env, stub_iam):
    client = auth_as(stub_iam, api_env, user_id=1001)

    # Inverted dates -> 400 Bad Request
    res = client.post(
        "/api/v1/leave/applications/",
        data={
            "leave_type_code": "CL",
            "start_date": "2026-10-20",
            "end_date": "2026-10-10",
            "reason": "Invalid",
        },
        HTTP_AUTHORIZATION="Token tok-123",
    )
    assert res.status_code == 400

    # Non-existent leave type -> 404 Not Found
    res2 = client.post(
        "/api/v1/leave/applications/",
        data={
            "leave_type_code": "UNKNOWN",
            "start_date": "2026-10-10",
            "end_date": "2026-10-12",
            "reason": "Invalid",
        },
        HTTP_AUTHORIZATION="Token tok-123",
    )
    assert res2.status_code == 404


@pytest.mark.django_db
def test_insufficient_balance_conflict(api_env, stub_iam):
    client = auth_as(stub_iam, api_env, user_id=1001)
    res = client.post(
        "/api/v1/leave/applications/",
        data={
            "leave_type_code": "CL",
            "start_date": "2026-10-01",
            "end_date": "2026-10-20",
            "reason": "Exceeding balance",
        },
        HTTP_AUTHORIZATION="Token tok-123",
    )
    assert res.status_code == 409


# 3. Substitute Operations


@pytest.mark.django_db
def test_substitute_workflow(api_env, stub_iam):
    alice_client = auth_as(stub_iam, api_env, user_id=1001)

    apply_res = alice_client.post(
        "/api/v1/leave/applications/",
        data={
            "leave_type_code": "EL",
            "start_date": "2026-11-01",
            "end_date": "2026-11-05",
            "reason": "Conference",
            "substitute_user_id": 1002,
        },
        HTTP_AUTHORIZATION="Token tok-123",
    )
    assert apply_res.status_code == 201
    assert apply_res.json()["status"] == "awaiting_substitute"

    # Bob views pending substitute nominations
    bob_client = auth_as(stub_iam, api_env, user_id=1002)
    sub_res = bob_client.get(
        "/api/v1/leave/substitute/nominations/", HTTP_AUTHORIZATION="Token tok-123"
    )
    assert sub_res.status_code == 200
    noms = sub_res.json()
    assert len(noms) == 1
    nom_id = noms[0]["id"]

    # Alice should not see Bob's nomination in her inbox
    alice_client = auth_as(stub_iam, api_env, user_id=1001)
    alice_subs = alice_client.get(
        "/api/v1/leave/substitute/nominations/", HTTP_AUTHORIZATION="Token tok-123"
    )
    assert alice_subs.status_code == 200
    assert len(alice_subs.json()) == 0

    # Alice cannot respond to Bob's nomination
    alice_respond = alice_client.post(
        f"/api/v1/leave/substitute/nominations/{nom_id}/respond/",
        data={"decision": "accepted"},
        HTTP_AUTHORIZATION="Token tok-123",
    )
    assert alice_respond.status_code == 403

    # Bob accepts nomination
    bob_client = auth_as(stub_iam, api_env, user_id=1002)
    bob_respond = bob_client.post(
        f"/api/v1/leave/substitute/nominations/{nom_id}/respond/",
        data={"decision": "accepted", "remarks": "Glad to cover"},
        HTTP_AUTHORIZATION="Token tok-123",
    )
    assert bob_respond.status_code == 200
    assert bob_respond.json()["status"] == "accepted"


# 4. Approver Operations & Department Scoping


@pytest.mark.django_db
def test_hod_department_isolation_and_approval(api_env, stub_iam):
    alice_client = auth_as(stub_iam, api_env, user_id=1001)

    apply_res = alice_client.post(
        "/api/v1/leave/applications/",
        data={
            "leave_type_code": "CL",
            "start_date": "2026-10-15",
            "end_date": "2026-10-16",
            "reason": "Personal",
        },
        HTTP_AUTHORIZATION="Token tok-123",
    )
    req_id = apply_res.json()["id"]

    # HOD CSE (department: Computer Science & Engineering)
    hod_cse = auth_as(
        stub_iam,
        api_env,
        user_id=2001,
        roles=("HOD",),
        permissions=("leave.request.view_self", "leave.request.approve"),
    )
    cse_queue = hod_cse.get("/api/v1/leave/approvals/", HTTP_AUTHORIZATION="Token tok-123")
    assert cse_queue.status_code == 200
    assert len(cse_queue.json()) == 1
    assert cse_queue.json()[0]["id"] == req_id

    # HOD ME (department: Mechanical Engineering)
    hod_me = auth_as(
        stub_iam,
        api_env,
        user_id=2002,
        roles=("HOD",),
        permissions=("leave.request.view_self", "leave.request.approve"),
    )
    me_queue = hod_me.get("/api/v1/leave/approvals/", HTTP_AUTHORIZATION="Token tok-123")
    assert me_queue.status_code == 200
    assert len(me_queue.json()) == 0

    # HOD ME cannot view request detail
    me_det = hod_me.get(f"/api/v1/leave/requests/{req_id}/", HTTP_AUTHORIZATION="Token tok-123")
    assert me_det.status_code == 403

    # HOD ME cannot review request
    me_review = hod_me.post(
        f"/api/v1/leave/approvals/{req_id}/review/",
        data={"decision": "approve", "remarks": "Unauthorized cross-dept approval"},
        HTTP_AUTHORIZATION="Token tok-123",
    )
    assert me_review.status_code == 403

    # HOD CSE reviews and approves CL (final authority)
    hod_cse = auth_as(
        stub_iam,
        api_env,
        user_id=2001,
        roles=("HOD",),
        permissions=("leave.request.view_self", "leave.request.approve"),
    )
    cse_review = hod_cse.post(
        f"/api/v1/leave/approvals/{req_id}/review/",
        data={"decision": "approve", "remarks": "Approved by HOD"},
        HTTP_AUTHORIZATION="Token tok-123",
    )
    assert cse_review.status_code == 200
    assert cse_review.json()["status"] == "approved"


@pytest.mark.django_db
def test_multistep_sanction_workflow(api_env, stub_iam):
    alice_client = auth_as(stub_iam, api_env, user_id=1001)

    apply_res = alice_client.post(
        "/api/v1/leave/applications/",
        data={
            "leave_type_code": "EL",
            "start_date": "2026-11-10",
            "end_date": "2026-11-14",
            "reason": "Training",
            "substitute_user_id": 1002,
        },
        HTTP_AUTHORIZATION="Token tok-123",
    )
    req_id = apply_res.json()["id"]

    # Bob accepts
    bob_client = auth_as(stub_iam, api_env, user_id=1002)
    nom_id = SubstituteNomination.objects.get(request_id=req_id).id
    bob_client.post(
        f"/api/v1/leave/substitute/nominations/{nom_id}/respond/",
        data={"decision": "accepted"},
        HTTP_AUTHORIZATION="Token tok-123",
    )

    # HOD CSE recommends
    hod_cse = auth_as(
        stub_iam,
        api_env,
        user_id=2001,
        roles=("HOD",),
        permissions=("leave.request.view_self", "leave.request.approve"),
    )
    rec_res = hod_cse.post(
        f"/api/v1/leave/approvals/{req_id}/review/",
        data={"decision": "recommend", "remarks": "Strongly recommended"},
        HTTP_AUTHORIZATION="Token tok-123",
    )
    assert rec_res.status_code == 200
    assert rec_res.json()["status"] == "awaiting_sanction"

    # Dean sanctions
    dean_client = auth_as(
        stub_iam,
        api_env,
        user_id=3001,
        roles=("Dean Academic",),
        permissions=("leave.request.view_self", "leave.request.approve"),
    )
    dean_res = dean_client.post(
        f"/api/v1/leave/approvals/{req_id}/sanction/",
        data={"decision": "approve", "remarks": "Sanctioned"},
        HTTP_AUTHORIZATION="Token tok-123",
    )
    assert dean_res.status_code == 200
    assert dean_res.json()["status"] == "approved"


# 5. Cancellation, Extension, Resumption Lifecycle


@pytest.mark.django_db
def test_cancellation_workflow(api_env, stub_iam):
    alice_client = auth_as(stub_iam, api_env, user_id=1001)

    apply_res = alice_client.post(
        "/api/v1/leave/applications/",
        data={
            "leave_type_code": "CL",
            "start_date": "2026-12-01",
            "end_date": "2026-12-02",
            "reason": "Trip",
        },
        HTTP_AUTHORIZATION="Token tok-123",
    )
    req_id = apply_res.json()["id"]

    hod_cse = auth_as(
        stub_iam,
        api_env,
        user_id=2001,
        roles=("HOD",),
        permissions=("leave.request.view_self", "leave.request.approve"),
    )
    hod_cse.post(
        f"/api/v1/leave/approvals/{req_id}/review/",
        data={"decision": "approve"},
        HTTP_AUTHORIZATION="Token tok-123",
    )

    # Alice requests cancellation
    alice_client = auth_as(stub_iam, api_env, user_id=1001)
    cancel_res = alice_client.post(
        f"/api/v1/leave/requests/{req_id}/cancel/",
        data={"reason": "Trip cancelled"},
        HTTP_AUTHORIZATION="Token tok-123",
    )
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "cancellation_pending_unit_head"

    # HOD reviews and approves cancellation
    hod_cse = auth_as(
        stub_iam,
        api_env,
        user_id=2001,
        roles=("HOD",),
        permissions=("leave.request.view_self", "leave.request.approve"),
    )
    hod_cancel = hod_cse.post(
        f"/api/v1/leave/approvals/{req_id}/review/",
        data={"decision": "approve", "remarks": "Cancellation approved"},
        HTTP_AUTHORIZATION="Token tok-123",
    )
    assert hod_cancel.status_code == 200
    assert hod_cancel.json()["status"] == "cancelled"


@pytest.mark.django_db
def test_extension_and_resumption_lifecycle(api_env, stub_iam):
    today = date.today()
    req = LeaveRequest.objects.create(
        user_id=1001,
        leave_type=api_env["el"],
        cadre="faculty",
        department="Computer Science & Engineering",
        start_date=today - timedelta(days=2),
        end_date=today + timedelta(days=2),
        requested_days=Decimal("5.0"),
        reason="Work trip",
        status=LeaveState.APPROVED,
    )
    bal = LeaveBalance.objects.get(user_id=1001, leave_type=api_env["el"], year=today.year)
    bal.used_days = Decimal("5.0")
    bal.available_days = Decimal("25.0")
    bal.save()

    # Alice requests extension
    alice_client = auth_as(stub_iam, api_env, user_id=1001)
    ext_end = today + timedelta(days=4)
    ext_res = alice_client.post(
        f"/api/v1/leave/requests/{req.id}/extend/",
        data={"extension_end_date": ext_end.isoformat(), "reason": "More work"},
        HTTP_AUTHORIZATION="Token tok-123",
    )
    assert ext_res.status_code == 200
    assert ext_res.json()["status"] == "awaiting_extension_unit_head"

    # HOD reviews extension
    hod_cse = auth_as(
        stub_iam,
        api_env,
        user_id=2001,
        roles=("HOD",),
        permissions=("leave.request.view_self", "leave.request.approve"),
    )
    ext_rec = hod_cse.post(
        f"/api/v1/leave/approvals/{req.id}/review/",
        data={"decision": "recommend", "remarks": "Extension recommended"},
        HTTP_AUTHORIZATION="Token tok-123",
    )
    assert ext_rec.status_code == 200
    assert ext_rec.json()["status"] == "extension_pending_sanction"

    # Dean sanctions extension
    dean_client = auth_as(
        stub_iam,
        api_env,
        user_id=3001,
        roles=("Dean Academic",),
        permissions=("leave.request.view_self", "leave.request.approve"),
    )
    ext_sanction = dean_client.post(
        f"/api/v1/leave/approvals/{req.id}/sanction/",
        data={"decision": "approve", "remarks": "Extension approved"},
        HTTP_AUTHORIZATION="Token tok-123",
    )
    assert ext_sanction.status_code == 200
    assert ext_sanction.json()["status"] == "extended"

    # Alice submits duty resumption
    alice_client = auth_as(stub_iam, api_env, user_id=1001)
    actual_resumption = ext_end + timedelta(days=1)
    resume_res = alice_client.post(
        f"/api/v1/leave/requests/{req.id}/resume/",
        data={
            "actual_resumption_date": actual_resumption.isoformat(),
            "remarks": "Resumed duty on time",
        },
        HTTP_AUTHORIZATION="Token tok-123",
    )
    assert resume_res.status_code == 200
    assert resume_res.json()["decision"] == "pending"
    req.refresh_from_db()
    assert req.status == "resumption_review_pending"

    # Approver reviews resumption
    dean_client = auth_as(
        stub_iam,
        api_env,
        user_id=3001,
        roles=("Dean Academic",),
        permissions=("leave.request.view_self", "leave.request.approve"),
    )
    resume_review = dean_client.post(
        f"/api/v1/leave/approvals/{req.id}/resumption/",
        data={"decision": "approved", "remarks": "Duty resumed"},
        HTTP_AUTHORIZATION="Token tok-123",
    )
    assert resume_review.status_code == 200
    assert resume_review.json()["decision"] == "approved"
    req.refresh_from_db()
    assert req.status == "resumption_reviewed_no_adjustment"


# 6. Admin Offline Leave Operations


@pytest.mark.django_db
def test_admin_offline_leave_recording(api_env, stub_iam):
    alice_client = auth_as(stub_iam, api_env, user_id=1001)
    res_forbidden = alice_client.post(
        "/api/v1/leave/admin/offline/",
        data={
            "employee_user_id": 1001,
            "leave_type_code": "CL",
            "start_date": "2026-09-01",
            "end_date": "2026-09-02",
            "reason": "Offline sanction",
            "offline_sanction_reference": "REF/2026/001",
            "offline_sanctioned_by": "Dean Academic",
            "offline_sanctioned_date": "2026-08-30",
        },
        HTTP_AUTHORIZATION="Token tok-123",
    )
    assert res_forbidden.status_code == 403

    admin_client = auth_as(
        stub_iam,
        api_env,
        user_id=5001,
        roles=("Leave Administrator",),
        permissions=(
            "leave.request.view_self",
            "leave.balance.update",
            "leave.type.manage",
        ),
    )
    res_admin = admin_client.post(
        "/api/v1/leave/admin/offline/",
        data={
            "employee_user_id": 1001,
            "leave_type_code": "CL",
            "start_date": "2026-09-01",
            "end_date": "2026-09-02",
            "reason": "Offline sanction",
            "offline_sanction_reference": "REF/2026/001",
            "offline_sanctioned_by": "Dean Academic",
            "offline_sanctioned_date": "2026-08-30",
        },
        HTTP_AUTHORIZATION="Token tok-123",
    )
    assert res_admin.status_code == 201
    created = res_admin.json()
    assert created["status"] == "approved"
    assert created["is_offline_record"] is True
    assert created["offline_sanction_reference"] == "REF/2026/001"


# 7. Targeted Tests for Review Flag 1: DELETE /api/v1/leave/applications/ Backward-Compatible Withdrawal


@pytest.mark.django_db
def test_delete_application_stub_cannot_bypass_withdrawal_workflow(api_env, stub_iam):
    alice_client = auth_as(stub_iam, api_env, user_id=1001)

    # 1. Calling DELETE without an ID returns 400 Bad Request
    res_no_id = alice_client.delete(
        "/api/v1/leave/applications/",
        HTTP_AUTHORIZATION="Token tok-123",
    )
    assert res_no_id.status_code == 400
    assert "A valid request ID must be provided" in res_no_id.json()["error"]["message"]

    # 2. Create a pending request
    apply_res = alice_client.post(
        "/api/v1/leave/applications/",
        data={
            "leave_type_code": "CL",
            "start_date": "2026-10-15",
            "end_date": "2026-10-16",
            "reason": "Family work",
        },
        HTTP_AUTHORIZATION="Token tok-123",
    )
    req_id = apply_res.json()["id"]

    # 3. Non-owner (Bob) attempts to withdraw via DELETE /api/v1/leave/applications/?id=... -> 403 Forbidden
    bob_client = auth_as(stub_iam, api_env, user_id=1002)
    bob_del = bob_client.delete(
        f"/api/v1/leave/applications/?id={req_id}",
        HTTP_AUTHORIZATION="Token tok-123",
    )
    assert bob_del.status_code == 403

    # 4. Legitimate withdrawal by owner (Alice) via DELETE invokes withdraw_leave_request
    alice_client = auth_as(stub_iam, api_env, user_id=1001)
    alice_del = alice_client.delete(
        f"/api/v1/leave/applications/?id={req_id}",
        HTTP_AUTHORIZATION="Token tok-123",
    )
    assert alice_del.status_code == 200
    assert alice_del.json()["status"] == "withdrawn"

    # 5. Calling DELETE again on already-withdrawn request fails with 409 Conflict
    alice_del_again = alice_client.delete(
        f"/api/v1/leave/applications/?id={req_id}",
        HTTP_AUTHORIZATION="Token tok-123",
    )
    assert alice_del_again.status_code == 409


# 8. Targeted Tests for Review Flag 2: Admin Dispatcher and Role Guardrails


@pytest.mark.django_db
def test_admin_dispatcher_requires_authorized_admin_roles(api_env, stub_iam):
    # Non-admin user who possesses leave.balance.update but lacks ADMIN_ROLES ("Leave Administrator", "hr_officer")
    approver_with_balance_perm = auth_as(
        stub_iam,
        api_env,
        user_id=2001,
        roles=("HOD",),
        permissions=(
            "leave.request.view_self",
            "leave.request.approve",
            "leave.balance.update",
        ),
    )

    # 1. Admin offline endpoint rejected with 403
    res_offline = approver_with_balance_perm.post(
        "/api/v1/leave/admin/offline/",
        data={
            "employee_user_id": 1001,
            "leave_type_code": "CL",
            "start_date": "2026-09-01",
            "end_date": "2026-09-02",
            "reason": "Offline sanction attempt",
            "offline_sanction_reference": "REF/2026/002",
            "offline_sanctioned_by": "Director",
            "offline_sanctioned_date": "2026-08-30",
        },
        HTTP_AUTHORIZATION="Token tok-123",
    )
    assert res_offline.status_code == 403
    assert "Leave Administrators or HR Officers" in res_offline.json()["error"]["message"]

    # 2. General admin dispatcher rejected with 403
    res_admin_dispatch = approver_with_balance_perm.post(
        "/api/v1/leave/admin/",
        data={"action": "update_policy"},
        HTTP_AUTHORIZATION="Token tok-123",
    )
    assert res_admin_dispatch.status_code == 403
    assert "Leave Administrators or HR Officers" in res_admin_dispatch.json()["error"]["message"]

    # 3. Authorized admin without leave.type.manage permission cannot manage policies
    admin_without_type_manage = auth_as(
        stub_iam,
        api_env,
        user_id=5001,
        roles=("Leave Administrator",),
        permissions=(
            "leave.request.view_self",
            "leave.balance.update",
        ),
    )
    res_policy_denied = admin_without_type_manage.post(
        "/api/v1/leave/admin/",
        data={"action": "update_policy"},
        HTTP_AUTHORIZATION="Token tok-123",
    )
    assert res_policy_denied.status_code == 403
    assert "leave types or policies" in res_policy_denied.json()["error"]["message"]


# 9. Targeted Tests for Review Flag 3: Department Scope and Approval Stage Enforcement


@pytest.mark.django_db
def test_approval_queue_and_detail_enforce_department_and_exact_stage(api_env, stub_iam):
    alice_client = auth_as(stub_iam, api_env, user_id=1001)

    # 1. Create a request that requires substitute (EL) -> starts in 'awaiting_substitute'
    apply_res = alice_client.post(
        "/api/v1/leave/applications/",
        data={
            "leave_type_code": "EL",
            "start_date": "2026-11-20",
            "end_date": "2026-11-25",
            "reason": "Research visit",
            "substitute_user_id": 1002,
        },
        HTTP_AUTHORIZATION="Token tok-123",
    )
    el_req_id = apply_res.json()["id"]
    assert apply_res.json()["status"] == "awaiting_substitute"

    # Approvers (HOD or Dean) CANNOT view unsubmitted/substitute-pending requests in detail
    hod_cse = auth_as(
        stub_iam,
        api_env,
        user_id=2001,
        roles=("HOD",),
        permissions=("leave.request.view_self", "leave.request.approve"),
    )
    hod_view_unsubmitted = hod_cse.get(
        f"/api/v1/leave/requests/{el_req_id}/",
        HTTP_AUTHORIZATION="Token tok-123",
    )
    assert hod_view_unsubmitted.status_code == 403
    assert "not yet submitted" in hod_view_unsubmitted.json()["error"]["message"]

    dean_client = auth_as(
        stub_iam,
        api_env,
        user_id=3001,
        roles=("Dean Academic",),
        permissions=("leave.request.view_self", "leave.request.approve"),
    )
    dean_view_unsubmitted = dean_client.get(
        f"/api/v1/leave/requests/{el_req_id}/",
        HTTP_AUTHORIZATION="Token tok-123",
    )
    assert dean_view_unsubmitted.status_code == 403

    # 2. Substitute accepts -> moves to 'awaiting_unit_head'
    bob_client = auth_as(stub_iam, api_env, user_id=1002)
    nom_id = SubstituteNomination.objects.get(request_id=el_req_id).id
    bob_client.post(
        f"/api/v1/leave/substitute/nominations/{nom_id}/respond/",
        data={"decision": "accepted"},
        HTTP_AUTHORIZATION="Token tok-123",
    )

    # Now HOD CSE sees it in approvals queue; Dean does NOT see it (not yet at sanction stage)
    hod_cse = auth_as(
        stub_iam,
        api_env,
        user_id=2001,
        roles=("HOD",),
        permissions=("leave.request.view_self", "leave.request.approve"),
    )
    hod_cse_queue = hod_cse.get("/api/v1/leave/approvals/", HTTP_AUTHORIZATION="Token tok-123")
    assert hod_cse_queue.status_code == 200
    assert any(r["id"] == el_req_id for r in hod_cse_queue.json())

    dean_client = auth_as(
        stub_iam,
        api_env,
        user_id=3001,
        roles=("Dean Academic",),
        permissions=("leave.request.view_self", "leave.request.approve"),
    )
    dean_queue = dean_client.get("/api/v1/leave/approvals/", HTTP_AUTHORIZATION="Token tok-123")
    assert dean_queue.status_code == 200
    assert not any(r["id"] == el_req_id for r in dean_queue.json())

    # HOD ME (different department) does NOT see it in queue, and cannot view detail
    hod_me = auth_as(
        stub_iam,
        api_env,
        user_id=2002,
        roles=("HOD",),
        permissions=("leave.request.view_self", "leave.request.approve"),
    )
    hod_me_queue = hod_me.get("/api/v1/leave/approvals/", HTTP_AUTHORIZATION="Token tok-123")
    assert hod_me_queue.status_code == 200
    assert not any(r["id"] == el_req_id for r in hod_me_queue.json())

    hod_me_detail = hod_me.get(
        f"/api/v1/leave/requests/{el_req_id}/",
        HTTP_AUTHORIZATION="Token tok-123",
    )
    assert hod_me_detail.status_code == 403
    assert "outside your department" in hod_me_detail.json()["error"]["message"]

    # 3. HOD CSE recommends -> moves to 'awaiting_sanction'
    hod_cse = auth_as(
        stub_iam,
        api_env,
        user_id=2001,
        roles=("HOD",),
        permissions=("leave.request.view_self", "leave.request.approve"),
    )
    hod_cse.post(
        f"/api/v1/leave/approvals/{el_req_id}/review/",
        data={"decision": "recommend", "remarks": "Approved by HOD"},
        HTTP_AUTHORIZATION="Token tok-123",
    )

    # In 'awaiting_sanction':
    # HOD CSE no longer sees it in their queue (stage is awaiting_sanction)
    hod_cse_queue2 = hod_cse.get("/api/v1/leave/approvals/", HTTP_AUTHORIZATION="Token tok-123")
    assert hod_cse_queue2.status_code == 200
    assert not any(r["id"] == el_req_id for r in hod_cse_queue2.json())

    # Dean NOW sees it in their approvals queue
    dean_client = auth_as(
        stub_iam,
        api_env,
        user_id=3001,
        roles=("Dean Academic",),
        permissions=("leave.request.view_self", "leave.request.approve"),
    )
    dean_queue2 = dean_client.get("/api/v1/leave/approvals/", HTTP_AUTHORIZATION="Token tok-123")
    assert dean_queue2.status_code == 200
    assert any(r["id"] == el_req_id for r in dean_queue2.json())
