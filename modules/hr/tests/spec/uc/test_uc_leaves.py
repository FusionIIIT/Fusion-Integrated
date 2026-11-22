"""UC spec tests for Leave Application, Decision, and Tracking."""

from decimal import Decimal

import pytest

from modules.hr.models import LeaveBalance, LeaveRequest
from modules.hr.services import leaves
from modules.hr.tests.spec.conftest import (
    UID_FACULTY_1,
    UID_FACULTY_2,
    UID_HOD,
    UID_HR_ADMIN,
    UID_REGISTRAR,
    UID_UNAUTHORIZED,
    ensure_employee,
    ensure_workflow_route,
    make_actor,
)

pytestmark = pytest.mark.django_db


def test_uc_007_main_flow_submit_leave_request(hr_caller):
    """TEST-UC-007 | HR-UC-003 Main Flow.

    Verify that an Employee can submit a valid leave request that validates balance/eligibility, enters the approval workflow, and triggers notifications.
    """
    emp = ensure_employee(UID_FACULTY_1, kind="faculty")
    ensure_workflow_route("faculty", "leave_casual")
    LeaveBalance.objects.update_or_create(
        employee=emp,
        leave_type="casual",
        defaults={
            "available_days": Decimal("10.00"),
            "is_eligible": True,
            "updated_by_user_id": UID_HR_ADMIN,
        },
    )
    res = hr_caller(
        "post",
        "/api/v1/hr/leaves/create/",
        user_id=UID_FACULTY_1,
        role="faculty",
        data={"leave_type": "casual", "duration_days": "2.00", "justification": "Conference"},
    )
    assert res.status_code == 201
    assert res.data["status"] == "pending_authority"


def test_uc_008_alternative_a1_invalid_leave_validation(hr_caller):
    """TEST-UC-008 | HR-UC-003 Alternative A1.

    Verify that if leave validation does not pass (e.g. insufficient balance or missing fields), the request is rejected and does not enter the workflow.
    """
    emp = ensure_employee(UID_FACULTY_1, kind="faculty")
    bal, _ = LeaveBalance.objects.update_or_create(
        employee=emp,
        leave_type="casual",
        defaults={
            "available_days": Decimal("1.00"),
            "is_eligible": True,
            "updated_by_user_id": UID_HR_ADMIN,
        },
    )
    bal.available_days = Decimal("1.00")
    bal.save()
    res = hr_caller(
        "post",
        "/api/v1/hr/leaves/create/",
        user_id=UID_FACULTY_1,
        role="faculty",
        data={"leave_type": "casual", "duration_days": "10.00", "justification": "Too long"},
    )
    assert res.status_code == 422


def test_uc_009_exception_e1_unauthorized_leave_submission(hr_caller):
    """TEST-UC-009 | HR-UC-003 Exception E1.

    Verify that if RBAC denies the leave submission action, HR-EIS blocks submission and does not create a routed request.
    """
    res = hr_caller(
        "post",
        "/api/v1/hr/leaves/create/",
        user_id=UID_UNAUTHORIZED,
        role="student",
        kind="student",
        permissions=(),
        data={"leave_type": "casual", "duration_days": "1.00", "justification": "Test"},
    )
    assert res.status_code == 403


def test_uc_010_main_flow_approve_leave(hr_caller):
    """TEST-UC-010 | HR-UC-004 Main Flow.

    Verify that Approving Authority can review a pending request and approve it, executing automatic balance update for leave or accountant handoff for claims.
    """
    emp = ensure_employee(UID_FACULTY_1, kind="faculty")
    ensure_workflow_route("faculty", "leave_casual")
    LeaveBalance.objects.update_or_create(
        employee=emp,
        leave_type="casual",
        defaults={
            "available_days": Decimal("10.00"),
            "is_eligible": True,
            "updated_by_user_id": UID_HR_ADMIN,
        },
    )
    req = leaves.submit_leave_request(
        actor=make_actor(UID_FACULTY_1, role="faculty"),
        leave_type="casual",
        duration_days=Decimal("2.00"),
        justification="Personal",
    )
    approver = make_actor(
        req.current_authority_user_id or UID_HOD, role="Head of Department", kind="faculty"
    )
    decided = leaves.decide_leave_request(actor=approver, request_id=req.pk, action="approve")
    assert decided.status == "approved"


def test_uc_011_alternative_a1_reject_leave(hr_caller):
    """TEST-UC-011 | HR-UC-004 Alternative A1.

    Verify that Approving Authority can reject a pending request, recording rejection remarks and ending the approval path.
    """
    emp = ensure_employee(UID_FACULTY_1, kind="faculty")
    ensure_workflow_route("faculty", "leave_casual")
    LeaveBalance.objects.update_or_create(
        employee=emp,
        leave_type="casual",
        defaults={
            "available_days": Decimal("10.00"),
            "is_eligible": True,
            "updated_by_user_id": UID_HR_ADMIN,
        },
    )
    req = leaves.submit_leave_request(
        actor=make_actor(UID_FACULTY_1, role="faculty"),
        leave_type="casual",
        duration_days=Decimal("1.00"),
        justification="Personal",
    )
    approver = make_actor(
        req.current_authority_user_id or UID_HOD, role="Head of Department", kind="faculty"
    )
    decided = leaves.decide_leave_request(
        actor=approver, request_id=req.pk, action="reject", note="Staffing shortage"
    )
    assert decided.status == "rejected"


def test_uc_012_alternative_a2_forward_leave(hr_caller):
    """TEST-UC-012 | HR-UC-004 Alternative A2.

    Verify that an intermediate Approving Authority can forward a pending request to the next configured authority in the hierarchy.
    """
    emp = ensure_employee(UID_FACULTY_1, kind="faculty")
    LeaveBalance.objects.update_or_create(
        employee=emp,
        leave_type="casual",
        defaults={
            "available_days": Decimal("10.00"),
            "is_eligible": True,
            "updated_by_user_id": UID_HR_ADMIN,
        },
    )
    make_actor(UID_FACULTY_1, role="faculty")
    req = LeaveRequest.objects.create(
        employee=emp,
        leave_type="casual",
        duration_days=Decimal("2.00"),
        justification="Personal",
        status="pending_authority",
        route_snapshot=[{"approver_user_id": UID_HOD}, {"approver_user_id": UID_REGISTRAR}],
        authority_step=0,
        current_authority_user_id=UID_HOD,
        submitted_by_user_id=UID_FACULTY_1,
    )
    approver = make_actor(UID_HOD, role="Head of Department", kind="faculty")
    decided = leaves.decide_leave_request(
        actor=approver, request_id=req.pk, action="forward", note="Recommended"
    )
    assert decided.status == "pending_next_authority"
    assert decided.current_authority_user_id == UID_REGISTRAR


def test_uc_013_exception_e1_unauthorized_or_out_of_order_leave_decision(hr_caller):
    """TEST-UC-013 | HR-UC-004 Exception E1.

    Verify that if the actor is not the current authorized authority or attempts to bypass/alter workflow order, HR-EIS blocks the decision.
    """
    emp = ensure_employee(UID_FACULTY_1, kind="faculty")
    ensure_workflow_route("faculty", "leave_casual")
    LeaveBalance.objects.update_or_create(
        employee=emp,
        leave_type="casual",
        defaults={
            "available_days": Decimal("10.00"),
            "is_eligible": True,
            "updated_by_user_id": UID_HR_ADMIN,
        },
    )
    req = leaves.submit_leave_request(
        actor=make_actor(UID_FACULTY_1, role="faculty"),
        leave_type="casual",
        duration_days=Decimal("1.00"),
        justification="Personal",
    )
    # Non-assigned authority attempts to decide
    res = hr_caller(
        "post",
        f"/api/v1/hr/leaves/{req.pk}/decision/",
        user_id=UID_FACULTY_2,
        role="faculty",
        data={"action": "approve"},
    )
    assert res.status_code == 403


def test_uc_014_main_flow_track_leave_request_status(hr_caller):
    """TEST-UC-014 | HR-UC-005 Main Flow.

    Verify that an Employee can track the current status and traceable progression history of their own submitted HR requests.
    """
    ensure_employee(UID_FACULTY_1, kind="faculty")
    res = hr_caller("get", "/api/v1/hr/leaves/", user_id=UID_FACULTY_1, role="faculty")
    assert res.status_code == 200


def test_uc_015_alternative_a1_no_matching_requests(hr_caller):
    """TEST-UC-015 | HR-UC-005 Alternative A1.

    Verify that when no matching request exists for the Employee, HR-EIS reports that no authorized matching request is available.
    """
    ensure_employee(UID_FACULTY_2, kind="faculty")
    res = hr_caller("get", "/api/v1/hr/leaves/", user_id=UID_FACULTY_2, role="faculty")
    assert res.status_code == 200
    assert isinstance(res.data.get("results"), list)


def test_uc_016_exception_e1_unauthorized_tracking_access(hr_caller):
    """TEST-UC-016 | HR-UC-005 Exception E1.

    Verify that if an Employee attempts to access another employee's request without an authorized role, HR-EIS denies access.
    """
    emp = ensure_employee(UID_FACULTY_1, kind="faculty")
    ensure_workflow_route("faculty", "leave_casual")
    LeaveBalance.objects.update_or_create(
        employee=emp,
        leave_type="casual",
        defaults={
            "available_days": Decimal("10.00"),
            "is_eligible": True,
            "updated_by_user_id": UID_HR_ADMIN,
        },
    )
    req = leaves.submit_leave_request(
        actor=make_actor(UID_FACULTY_1, role="faculty"),
        leave_type="casual",
        duration_days=Decimal("1.00"),
        justification="Personal",
    )
    # Employee 2 querying leaves only sees own
    res = hr_caller("get", "/api/v1/hr/leaves/", user_id=UID_FACULTY_2, role="faculty")
    assert res.status_code == 200
    assert not any(item["id"] == req.pk for item in res.data["results"])
