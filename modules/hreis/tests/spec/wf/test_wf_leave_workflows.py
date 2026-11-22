import pytest
from datetime import date
from core.api.exceptions import BadRequestError
from modules.hreis.models import EmployeeServiceRecord, HrAuditLog, LeaveRequest
from modules.hreis.services.leaves import decide_leave_request, submit_leave_request

pytestmark = pytest.mark.django_db


def test_wf_001_leave_direct_approval():
    """TEST-WF-001 [BW-HR-01 Direct Approval Path]: Verify finite path from draft to approved leave without forwarding."""
    rec = EmployeeServiceRecord.objects.create(
        user_id=501,
        employee_id="EMP0501",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
        leave_balances={"casual": 8},
    )
    leave = submit_leave_request(
        user_id=501,
        username="u501",
        leave_type="casual",
        start_date=date(2026, 12, 1),
        end_date=date(2026, 12, 2),
        duration_days=2,
        justification="Personal",
    )
    assert leave.status == "pending"
    decided = decide_leave_request(
        leave_id=leave.id,
        outcome="approved",
        remarks="Approved by HOD",
        actor_id=301,
        actor_username="hod",
        actor_role="hod",
    )
    assert decided.status == "approved"
    rec.refresh_from_db()
    assert rec.leave_balances["casual"] == 6


def test_wf_002_leave_validation_guard():
    """TEST-WF-002 [BW-HR-01 Validation Guard]: Verify invalid leave request fails validation guard."""
    EmployeeServiceRecord.objects.create(
        user_id=502,
        employee_id="EMP0502",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
        leave_balances={"casual": 1},
    )
    with pytest.raises(BadRequestError):
        submit_leave_request(
            user_id=502,
            username="u502",
            leave_type="casual",
            start_date=date(2026, 12, 1),
            end_date=date(2026, 12, 3),
            duration_days=3,
            justification="Exceeds balance",
        )


def test_wf_003_leave_rejection():
    """TEST-WF-003 [BW-HR-02 Rejection Path]: Verify finite workflow path from draft to rejection ending approval path."""
    rec = EmployeeServiceRecord.objects.create(
        user_id=503,
        employee_id="EMP0503",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
        leave_balances={"casual": 5},
    )
    leave = submit_leave_request(
        user_id=503,
        username="u503",
        leave_type="casual",
        start_date=date(2026, 12, 1),
        end_date=date(2026, 12, 1),
        duration_days=1,
        justification="Personal",
    )
    decided = decide_leave_request(
        leave_id=leave.id,
        outcome="rejected",
        remarks="Cannot approve due to departmental duties",
        actor_id=301,
        actor_username="hod",
        actor_role="hod",
    )
    assert decided.status == "rejected"
    rec.refresh_from_db()
    assert rec.leave_balances["casual"] == 5


def test_wf_004_leave_terminal_state_guard():
    """TEST-WF-004 [BW-HR-02 Terminal State Guard]: Verify rejected leave request cannot be approved subsequently."""
    rec = EmployeeServiceRecord.objects.create(
        user_id=504,
        employee_id="EMP0504",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
        leave_balances={"casual": 5},
    )
    leave = submit_leave_request(
        user_id=504,
        username="u504",
        leave_type="casual",
        start_date=date(2026, 12, 1),
        end_date=date(2026, 12, 1),
        duration_days=1,
        justification="Personal",
    )
    decide_leave_request(
        leave_id=leave.id,
        outcome="rejected",
        remarks="Rejected",
        actor_id=301,
        actor_username="hod",
        actor_role="hod",
    )
    with pytest.raises(BadRequestError):
        decide_leave_request(
            leave_id=leave.id,
            outcome="approved",
            remarks="Post rejection approval attempt",
            actor_id=301,
            actor_username="hod",
            actor_role="hod",
        )


def test_wf_005_leave_forward_one_traversal():
    """TEST-WF-005 [BW-HR-03 Forwarding Traversal Path]: Verify forwarding traversal before final approval."""
    rec = EmployeeServiceRecord.objects.create(
        user_id=505,
        employee_id="EMP0505",
        department="CSE",
        designation="Professor",
        category="faculty",
        leave_balances={"sabbatical": 180},
    )
    leave = submit_leave_request(
        user_id=505,
        username="u505",
        leave_type="sabbatical",
        start_date=date(2026, 12, 1),
        end_date=date(2027, 2, 28),
        duration_days=90,
        justification="Research Sabbatical",
    )
    fwd = decide_leave_request(
        leave_id=leave.id,
        outcome="forwarded",
        remarks="Forwarding to Director",
        actor_id=301,
        actor_username="hod",
        actor_role="hod",
    )
    assert fwd.status == "forwarded"
    approved = decide_leave_request(
        leave_id=leave.id,
        outcome="approved",
        remarks="Final approval by Director",
        actor_id=305,
        actor_username="director",
        actor_role="director",
    )
    assert approved.status == "approved"
    rec.refresh_from_db()
    assert rec.leave_balances["sabbatical"] == 90


def test_wf_006_forwarding_authority_guard():
    """TEST-WF-006 [BW-HR-03 Forwarding Authority Guard]: Verify non-current authority cannot decide request during traversal."""
    EmployeeServiceRecord.objects.create(
        user_id=506,
        employee_id="EMP0506",
        department="CSE",
        designation="Professor",
        category="faculty",
        leave_balances={"sabbatical": 180},
    )
    leave = submit_leave_request(
        user_id=506,
        username="u506",
        leave_type="sabbatical",
        start_date=date(2026, 12, 1),
        end_date=date(2027, 2, 28),
        duration_days=90,
        justification="Sabbatical",
    )
    decide_leave_request(
        leave_id=leave.id,
        outcome="forwarded",
        remarks="Forward to Director",
        actor_id=301,
        actor_username="hod",
        actor_role="hod",
    )
    with pytest.raises(BadRequestError):
        # Staff role attempting decision on Director-pending request
        decide_leave_request(
            leave_id=leave.id,
            outcome="approved",
            remarks="Unauthorized attempt",
            actor_id=999,
            actor_username="staff_user",
            actor_role="staff",
        )


def test_wf_007_cw_leave_lifecycle_approval():
    """TEST-WF-007 [CW-HR-01 Full Approval Lifecycle]: Verify composite leave lifecycle combining submission, routing, approval, balance deduction, and audit trail."""
    rec = EmployeeServiceRecord.objects.create(
        user_id=507,
        employee_id="EMP0507",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
        leave_balances={"medical": 15},
    )
    leave = submit_leave_request(
        user_id=507,
        username="u507",
        leave_type="medical",
        start_date=date(2026, 12, 5),
        end_date=date(2026, 12, 8),
        duration_days=4,
        justification="Medical emergency",
    )
    decided = decide_leave_request(
        leave_id=leave.id,
        outcome="approved",
        remarks="Approved by HOD",
        actor_id=301,
        actor_username="hod",
        actor_role="hod",
    )
    assert decided.status == "approved"
    rec.refresh_from_db()
    assert rec.leave_balances["medical"] == 11
    assert HrAuditLog.objects.filter(entity_type="leave_request", entity_id=str(leave.id)).count() >= 2


def test_wf_008_cw_leave_lifecycle_rejection():
    """TEST-WF-008 [CW-HR-01 Full Rejection Lifecycle]: Verify composite leave lifecycle with rejection preserves audit history and balance integrity."""
    rec = EmployeeServiceRecord.objects.create(
        user_id=508,
        employee_id="EMP0508",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
        leave_balances={"casual": 6},
    )
    leave = submit_leave_request(
        user_id=508,
        username="u508",
        leave_type="casual",
        start_date=date(2026, 12, 1),
        end_date=date(2026, 12, 2),
        duration_days=2,
        justification="Personal",
    )
    decided = decide_leave_request(
        leave_id=leave.id,
        outcome="rejected",
        remarks="Not approved",
        actor_id=301,
        actor_username="hod",
        actor_role="hod",
    )
    assert decided.status == "rejected"
    rec.refresh_from_db()
    assert rec.leave_balances["casual"] == 6
    assert HrAuditLog.objects.filter(entity_type="leave_request", entity_id=str(leave.id), action="decide_leave_request").exists()


def test_wf_009_cw_leave_lifecycle_multi_tier():
    """TEST-WF-009 [CW-HR-01 Multi-Tier Forwarding Lifecycle]: Verify composite leave lifecycle with multi-tier routing through forwarding to final decision."""
    rec = EmployeeServiceRecord.objects.create(
        user_id=509,
        employee_id="EMP0509",
        department="CSE",
        designation="Professor",
        category="faculty",
        leave_balances={"sabbatical": 120},
    )
    leave = submit_leave_request(
        user_id=509,
        username="u509",
        leave_type="sabbatical",
        start_date=date(2026, 12, 1),
        end_date=date(2027, 1, 30),
        duration_days=60,
        justification="Book writing",
    )
    decide_leave_request(
        leave_id=leave.id,
        outcome="forwarded",
        remarks="Recommended",
        actor_id=301,
        actor_username="hod",
        actor_role="hod",
    )
    final = decide_leave_request(
        leave_id=leave.id,
        outcome="approved",
        remarks="Final approval",
        actor_id=305,
        actor_username="director",
        actor_role="director",
    )
    assert final.status == "approved"
    rec.refresh_from_db()
    assert rec.leave_balances["sabbatical"] == 60
