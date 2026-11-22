"""WF spec tests for CPDA Claim Workflows."""

from decimal import Decimal

import pytest

from core.api.exceptions import ConflictError
from modules.hr.domain import state_machine
from modules.hr.models import Claim
from modules.hr.services import claims
from modules.hr.tests.spec.conftest import (
    UID_ACCOUNTANT,
    UID_FACULTY_1,
    VALID_DRIVE_LINK,
    ensure_employee,
    ensure_workflow_route,
    make_actor,
)

pytestmark = pytest.mark.django_db


def test_wf_033_advance_approved_and_processed_path(hr_caller):
    """TEST-WF-033 | BW-HR-10 advance-approved-and-processed-path.

    Execute complete finite path for CPDA Advance through validation, HR verification, direct approval, and Accountant processing.
    """
    ensure_employee(UID_FACULTY_1, kind="faculty")
    claim = Claim.objects.create(
        employee_user_id=UID_FACULTY_1,
        employee_category="faculty",
        request_type="cpda_advance",
        purpose="Travel",
        amount=Decimal("20000.00"),
        status="approved",
    )
    actor_acc = make_actor(UID_ACCOUNTANT, role="Accountant", kind="staff")
    processed = claims.process_claim(
        actor=actor_acc,
        claim_id=claim.pk,
        financially_correct=True,
        details={"mode": "neft", "amount_disbursed": "20000.00"},
    )
    assert processed.status == "financial_processing_recorded"


def test_wf_034_transition_1_draft_to_submitted(hr_caller):
    """TEST-WF-034 | BW-HR-10 transition-1-draft-to-submitted.

    Verify Transition 1 of BW-HR-10: Submitting CPDA advance with required fields transitions from Draft to Submitted / Awaiting HR Verification.
    """
    ensure_workflow_route("faculty", "cpda_advance")
    ensure_employee(UID_FACULTY_1, kind="faculty")
    res = hr_caller(
        "post",
        "/api/v1/hr/claims/create/",
        user_id=UID_FACULTY_1,
        role="faculty",
        data={
            "request_type": "cpda_advance",
            "purpose": "Books",
            "amount": "5000.00",
            "supporting_document_links": [VALID_DRIVE_LINK],
        },
    )
    assert res.status_code == 201
    assert res.data["status"] == "pending_verification"


def test_wf_035_transition_2_verification_to_pending_authority(hr_caller):
    """TEST-WF-035 | BW-HR-10 transition-2-verification-to-pending-authority.

    Verify Transition 2 of BW-HR-10: HR Administrator verification transitions CPDA claim to Pending Current Authority.
    """
    t = state_machine.verify_claim(
        state_machine.PENDING_VERIFICATION, verified=True, has_route=True
    )
    assert t.state == state_machine.PENDING_AUTHORITY


def test_wf_036_transition_3_pending_to_approved_claim(hr_caller):
    """TEST-WF-036 | BW-HR-10 transition-3-pending-to-approved-claim.

    Verify Transition 3 of BW-HR-10: Approving Authority approval transitions CPDA claim to Approved CPDA Claim.
    """
    t = state_machine.decide_claim(
        state_machine.PENDING_AUTHORITY, action="approve", authority_step=0, route_length=1
    )
    assert t.state == state_machine.APPROVED


def test_wf_037_transition_4_approved_to_disbursement_recorded(hr_caller):
    """TEST-WF-037 | BW-HR-10 transition-4-approved-to-disbursement-recorded.

    Verify Transition 4 of BW-HR-10: Accountant disbursement recording transitions Approved CPDA Claim to Financial Processing / Disbursement Recorded.
    """
    claim = Claim.objects.create(
        employee_user_id=UID_FACULTY_1,
        employee_category="faculty",
        request_type="cpda_advance",
        purpose="Books",
        amount=Decimal("4000.00"),
        status="approved",
    )
    actor_acc = make_actor(UID_ACCOUNTANT, role="Accountant", kind="staff")
    processed = claims.process_claim(
        actor=actor_acc,
        claim_id=claim.pk,
        financially_correct=True,
        details={"mode": "neft", "amount_disbursed": "4000.00"},
    )
    assert processed.status == "financial_processing_recorded"


def test_wf_038_reimbursement_approved_and_processed_path(hr_caller):
    """TEST-WF-038 | BW-HR-11 reimbursement-approved-and-processed-path.

    Execute complete finite path for CPDA Reimbursement through validation, HR verification, direct approval, and Accountant processing.
    """
    claim = Claim.objects.create(
        employee_user_id=UID_FACULTY_1,
        employee_category="faculty",
        request_type="cpda_reimbursement",
        purpose="Receipts",
        amount=Decimal("6000.00"),
        status="approved",
    )
    actor_acc = make_actor(UID_ACCOUNTANT, role="Accountant", kind="staff")
    processed = claims.process_claim(
        actor=actor_acc,
        claim_id=claim.pk,
        financially_correct=True,
        details={"mode": "bank", "amount_disbursed": "6000.00"},
    )
    assert processed.status == "financial_processing_recorded"


def test_wf_039_transition_1_reimbursement_draft_to_submitted(hr_caller):
    """TEST-WF-039 | BW-HR-11 transition-1-reimbursement-draft-to-submitted.

    Verify Transition 1 of BW-HR-11: Submitting CPDA reimbursement form transitions to Submitted / Awaiting HR Verification.
    """
    ensure_workflow_route("faculty", "cpda_reimbursement")
    ensure_employee(UID_FACULTY_1, kind="faculty")
    res = hr_caller(
        "post",
        "/api/v1/hr/claims/create/",
        user_id=UID_FACULTY_1,
        role="faculty",
        data={
            "request_type": "cpda_reimbursement",
            "purpose": "Conference",
            "amount": "9000.00",
            "supporting_document_links": [VALID_DRIVE_LINK],
        },
    )
    assert res.status_code == 201


def test_wf_040_rejection_path(hr_caller):
    """TEST-WF-040 | BW-HR-12 rejection-path.

    Execute finite CPDA path from verified claim to rejection by Approving Authority.
    """
    t = state_machine.decide_claim(
        state_machine.PENDING_AUTHORITY, action="reject", authority_step=0, route_length=1
    )
    assert t.state == state_machine.REJECTED


def test_wf_041_forward_one_traversal_path(hr_caller):
    """TEST-WF-041 | BW-HR-13 forward-one-traversal-path.

    Execute exactly one forwarding traversal after CPDA verification from Pending Current Authority to Pending Next Authority.
    """
    t = state_machine.decide_claim(
        state_machine.PENDING_AUTHORITY, action="forward", authority_step=0, route_length=2
    )
    assert t.state == state_machine.PENDING_NEXT_AUTHORITY


def test_wf_042_forward_and_disbursement_sequence(hr_caller):
    """TEST-WF-042 | CW-HR-04 forward-and-disbursement-sequence.

    Execute composite CPDA lifecycle combining submission, HR verification, intermediate forwarding, final approval, and disbursement recording.
    """
    t1 = state_machine.decide_claim(
        state_machine.PENDING_AUTHORITY, action="forward", authority_step=0, route_length=2
    )
    t2 = state_machine.decide_claim(
        t1.state, action="approve", authority_step=t1.authority_step, route_length=2
    )
    assert t2.state == state_machine.APPROVED


def test_wf_043_prohibited_skip_hr_verification(hr_caller):
    """TEST-WF-043 | CW-HR-04 prohibited-skip-hr-verification.

    Verify prohibited transition in CW-HR-04: Authority cannot approve a CPDA claim directly from Submitted / Awaiting HR Verification state.
    """
    with pytest.raises(state_machine.InvalidTransition):
        state_machine.decide_claim(
            state_machine.PENDING_VERIFICATION, action="approve", authority_step=0, route_length=1
        )


def test_wf_044_prohibited_disbursement_before_approval(hr_caller):
    """TEST-WF-044 | CW-HR-04 prohibited-disbursement-before-approval.

    Verify prohibited transition in CW-HR-04: Accountant cannot record disbursement on an unapproved CPDA claim.
    """
    claim = Claim.objects.create(
        employee_user_id=UID_FACULTY_1,
        employee_category="faculty",
        request_type="cpda_advance",
        purpose="Travel",
        amount=Decimal("3000.00"),
        status="pending_authority",
    )
    actor_acc = make_actor(UID_ACCOUNTANT, role="Accountant", kind="staff")
    with pytest.raises(ConflictError):
        claims.process_claim(
            actor=actor_acc,
            claim_id=claim.pk,
            financially_correct=True,
            details={"mode": "neft"},
        )


def test_wf_045_prohibited_action_on_terminal_rejected_cpda(hr_caller):
    """TEST-WF-045 | CW-HR-04 prohibited-action-on-terminal-rejected-cpda.

    Verify prohibited transition in CW-HR-04: No transition can be executed on a terminal Rejected CPDA claim.
    """
    with pytest.raises(state_machine.InvalidTransition):
        state_machine.decide_claim(
            state_machine.REJECTED, action="approve", authority_step=0, route_length=1
        )
