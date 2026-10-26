from datetime import date

import pytest

from modules.elm.models import LeaveApproval, LeaveRequest
from modules.elm.services.approvals import decide_leave_request

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("category", ["CL", "RH"])
def test_unit_head_final_approval_for_cl_and_rh(category):
    leave = LeaveRequest.objects.create(
        employee_id=101,
        leave_category=category,
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 2),
        reason="Personal work",
    )

    result = decide_leave_request(
        request_id=leave.pk,
        actor_id=202,
        decision=LeaveApproval.Decision.APPROVED,
        permissions=["elm.approve.unit_head"],
    )

    result.refresh_from_db()
    assert result.status == LeaveRequest.Status.APPROVED
    assert result.approval_stage == LeaveRequest.ApprovalStage.COMPLETED
    assert result.final_approver_id == 202


def test_higher_sanction_leave_continues_after_unit_head():
    leave = LeaveRequest.objects.create(
        employee_id=101,
        leave_category="EL",
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 3),
        reason="Personal work",
    )

    result = decide_leave_request(
        request_id=leave.pk,
        actor_id=202,
        decision=LeaveApproval.Decision.APPROVED,
        permissions=["elm.approve.unit_head"],
    )

    result.refresh_from_db()
    assert result.status == LeaveRequest.Status.PENDING
    assert result.approval_stage == LeaveRequest.ApprovalStage.HIERARCHY


def test_unit_head_not_recommended_continues_higher_sanction():
    leave = LeaveRequest.objects.create(
        employee_id=101,
        leave_category="EL",
        start_date=date(2026, 11, 2),
        end_date=date(2026, 11, 3),
        reason="Personal work",
    )

    result = decide_leave_request(
        request_id=leave.pk,
        actor_id=202,
        decision=LeaveApproval.Decision.NOT_RECOMMENDED,
        comments="Not recommended by Unit Head",
        permissions=["elm.approve.unit_head"],
    )

    result.refresh_from_db()
    assert result.status == LeaveRequest.Status.PENDING
    assert result.approval_stage == LeaveRequest.ApprovalStage.HIERARCHY
    approval = LeaveApproval.objects.get(leave_request=leave)
    assert approval.decision == LeaveApproval.Decision.NOT_RECOMMENDED
