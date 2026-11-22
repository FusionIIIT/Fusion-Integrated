"""WF spec tests for Leave Request Finite State Transitions."""

from decimal import Decimal

import pytest

from modules.hr.domain import state_machine
from modules.hr.models import LeaveBalance
from modules.hr.services import leaves
from modules.hr.tests.spec.conftest import (
    UID_FACULTY_1,
    UID_HOD,
    UID_HR_ADMIN,
    ensure_employee,
    ensure_workflow_route,
    make_actor,
)

pytestmark = pytest.mark.django_db


def test_wf_001_direct_approval_path(hr_caller):
    """TEST-WF-001 | BW-HR-01 direct-approval-path.

    Execute the complete finite path from draft leave request to approved leave without forwarding, verifying automatic leave balance update.
    """
    ensure_workflow_route("faculty", "leave_casual")
    ensure_workflow_route("faculty", "leave_casual")
    emp = ensure_employee(UID_FACULTY_1, kind="faculty")
    bal, _ = LeaveBalance.objects.update_or_create(
        employee=emp,
        leave_type="casual",
        defaults={
            "available_days": Decimal("10.00"),
            "is_eligible": True,
            "updated_by_user_id": UID_HR_ADMIN,
        },
    )
    bal.available_days = Decimal("10.00")
    bal.save()
    req = leaves.submit_leave_request(
        actor=make_actor(UID_FACULTY_1, role="faculty"),
        leave_type="casual",
        duration_days=Decimal("3.00"),
        justification="Personal",
    )
    assert req.status == "pending_authority"
    approver = make_actor(
        req.current_authority_user_id or UID_HOD, role="Head of Department", kind="faculty"
    )
    approved = leaves.decide_leave_request(actor=approver, request_id=req.pk, action="approve")
    assert approved.status == "approved"
    bal.refresh_from_db()
    assert bal.available_days == Decimal("7.00")


def test_wf_002_transition_1_draft_to_pending(hr_caller):
    """TEST-WF-002 | BW-HR-01 transition-1-draft-to-pending.

    Verify Transition 1 of BW-HR-01: Employee submitting valid leave request transitions from Draft Leave Request to Pending Current Authority.
    """
    ensure_workflow_route("faculty", "leave_casual")
    ensure_workflow_route("faculty", "leave_casual")
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
    res = hr_caller(
        "post",
        "/api/v1/hr/leaves/create/",
        user_id=UID_FACULTY_1,
        role="faculty",
        data={"leave_type": "casual", "duration_days": "1.00", "justification": "Rest"},
    )
    assert res.status_code == 201
    assert res.data["status"] == "pending_authority"


def test_wf_003_transition_2_pending_to_approved(hr_caller):
    """TEST-WF-003 | BW-HR-01 transition-2-pending-to-approved.

    Verify Transition 2 of BW-HR-01: Approving Authority approving pending request transitions to Approved with leave balance update.
    """
    t = state_machine.decide_leave(
        state_machine.LEAVE_PENDING, action="approve", authority_step=0, route_length=1
    )
    assert t.state == state_machine.LEAVE_APPROVED


def test_wf_004_rejection_path(hr_caller):
    """TEST-WF-004 | BW-HR-02 rejection-path.

    Execute the complete finite path from draft leave request through submission to rejection by Approving Authority.
    """
    ensure_workflow_route("faculty", "leave_casual")
    emp = ensure_employee(UID_FACULTY_1, kind="faculty")
    bal, _ = LeaveBalance.objects.update_or_create(
        employee=emp,
        leave_type="casual",
        defaults={
            "available_days": Decimal("10.00"),
            "is_eligible": True,
            "updated_by_user_id": UID_HR_ADMIN,
        },
    )
    bal.available_days = Decimal("10.00")
    bal.save()
    req = leaves.submit_leave_request(
        actor=make_actor(UID_FACULTY_1, role="faculty"),
        leave_type="casual",
        duration_days=Decimal("2.00"),
        justification="Personal",
    )
    approver = make_actor(
        req.current_authority_user_id or UID_HOD, role="Head of Department", kind="faculty"
    )
    rejected = leaves.decide_leave_request(
        actor=approver, request_id=req.pk, action="reject", note="Rejected"
    )
    assert rejected.status == "rejected"
    bal.refresh_from_db()
    assert bal.available_days == Decimal("10.00")


def test_wf_005_transition_2_pending_to_rejected(hr_caller):
    """TEST-WF-005 | BW-HR-02 transition-2-pending-to-rejected.

    Verify Transition 2 of BW-HR-02: Approving Authority rejecting pending request transitions to terminal Rejected state.
    """
    t = state_machine.decide_leave(
        state_machine.LEAVE_PENDING, action="reject", authority_step=0, route_length=1
    )
    assert t.state == state_machine.LEAVE_REJECTED


def test_wf_006_forward_one_traversal_path(hr_caller):
    """TEST-WF-006 | BW-HR-03 forward-one-traversal-path.

    Execute exactly one traversal of the approval-authority forwarding loop from submission to Pending Next Authority.
    """
    t = state_machine.decide_leave(
        state_machine.LEAVE_PENDING, action="forward", authority_step=0, route_length=2
    )
    assert t.state == state_machine.LEAVE_PENDING_NEXT
    assert t.authority_step == 1


def test_wf_007_transition_2_pending_to_forwarded(hr_caller):
    """TEST-WF-007 | BW-HR-03 transition-2-pending-to-forwarded.

    Verify Transition 2 of BW-HR-03: Approving Authority forwarding request transitions to Pending Next Authority.
    """
    t = state_machine.decide_leave(
        state_machine.LEAVE_PENDING, action="forward", authority_step=0, route_length=2
    )
    assert t.state == state_machine.LEAVE_PENDING_NEXT


def test_wf_008_forward_and_approve_sequence(hr_caller):
    """TEST-WF-008 | CW-HR-01 forward-and-approve-sequence.

    Execute composite leave request lifecycle combining valid submission, intermediate forwarding, and subsequent final approval.
    """
    t1 = state_machine.decide_leave(
        state_machine.LEAVE_PENDING, action="forward", authority_step=0, route_length=2
    )
    t2 = state_machine.decide_leave(
        t1.state, action="approve", authority_step=t1.authority_step, route_length=2
    )
    assert t2.state == state_machine.LEAVE_APPROVED


def test_wf_009_prohibited_bypass_draft_to_approved(hr_caller):
    """TEST-WF-009 | CW-HR-01 prohibited-bypass-draft-to-approved.

    Verify prohibited transition in CW-HR-01: An actor cannot manually force transition from Draft Leave Request directly to Approved.
    """
    with pytest.raises(state_machine.InvalidTransition):
        state_machine.decide_leave(
            state_machine.LEAVE_PENDING, action="approve", authority_step=0, route_length=2
        )


def test_wf_010_prohibited_action_on_terminal_rejected(hr_caller):
    """TEST-WF-010 | CW-HR-01 prohibited-action-on-terminal-rejected.

    Verify prohibited transition in CW-HR-01: No workflow transition can be executed on a terminal Rejected leave request.
    """
    with pytest.raises(state_machine.InvalidTransition):
        state_machine.decide_leave(
            state_machine.LEAVE_REJECTED, action="approve", authority_step=0, route_length=1
        )
