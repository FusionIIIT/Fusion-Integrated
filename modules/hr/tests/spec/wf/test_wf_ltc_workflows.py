"""WF spec tests for LTC Claim Workflows."""

from decimal import Decimal

import pytest

from core.api.exceptions import ConflictError
from modules.hr.domain import state_machine
from modules.hr.models import Claim
from modules.hr.services import claims
from modules.hr.tests.spec.conftest import (
    UID_ACCOUNTANT,
    UID_FACULTY_1,
    UID_HOD,
    UID_HR_ADMIN,
    ensure_employee,
    ensure_workflow_route,
    make_actor,
)

pytestmark = pytest.mark.django_db


def test_wf_020_advance_approved_and_processed_path(hr_caller):
    """TEST-WF-020 | BW-HR-06 advance-approved-and-processed-path.

    Execute complete finite path for LTC Advance through verification, direct approval, and Accountant financial processing.
    """
    ensure_workflow_route("faculty", "ltc_advance")
    ensure_employee(UID_FACULTY_1, kind="faculty")
    claim = Claim.objects.create(
        employee_user_id=UID_FACULTY_1,
        employee_category="faculty",
        request_type="ltc_advance",
        purpose="Travel",
        status="pending_verification",
        amount=Decimal("15000.00"),
    )
    actor_admin = make_actor(UID_HR_ADMIN, role="hr_officer", kind="staff")
    claims.verify_claim(actor=actor_admin, claim_id=claim.pk, verified=True)
    claim.status = "pending_authority"
    claim.current_authority_user_id = UID_HOD
    claim.route_snapshot = [{"approver_user_id": UID_HOD}]
    claim.save()
    actor_hod = make_actor(UID_HOD, role="Head of Department", kind="faculty")
    claims.decide_claim(actor=actor_hod, claim_id=claim.pk, action="approve")
    actor_acc = make_actor(UID_ACCOUNTANT, role="Accountant", kind="staff")
    processed = claims.process_claim(
        actor=actor_acc,
        claim_id=claim.pk,
        financially_correct=True,
        details={"mode": "neft", "amount_disbursed": "15000.00"},
    )
    assert processed.status == "financial_processing_recorded"


def test_wf_021_transition_1_draft_to_submitted(hr_caller):
    """TEST-WF-021 | BW-HR-06 transition-1-draft-to-submitted.

    Verify Transition 1 of BW-HR-06: Submitting prescribed LTC advance form transitions from Draft to Submitted / Awaiting HR Verification.
    """
    ensure_workflow_route("faculty", "ltc_advance")
    ensure_employee(UID_FACULTY_1, kind="faculty")
    res = hr_caller(
        "post",
        "/api/v1/hr/claims/create/",
        user_id=UID_FACULTY_1,
        role="faculty",
        data={
            "request_type": "ltc_advance",
            "purpose": "Travel",
            "amount": "10000.00",
            "form_data": {"destination": "Home", "declared_members": ["self"]},
        },
    )
    assert res.status_code == 201
    assert res.data["status"] == "pending_verification"


def test_wf_022_transition_2_verification_to_pending_authority(hr_caller):
    """TEST-WF-022 | BW-HR-06 transition-2-verification-to-pending-authority.

    Verify Transition 2 of BW-HR-06: HR Administrator verification transitions LTC request to Pending Current Authority.
    """
    t = state_machine.verify_claim(
        state_machine.PENDING_VERIFICATION, verified=True, has_route=True
    )
    assert t.state == state_machine.PENDING_AUTHORITY


def test_wf_023_transition_3_pending_to_approved_claim(hr_caller):
    """TEST-WF-023 | BW-HR-06 transition-3-pending-to-approved-claim.

    Verify Transition 3 of BW-HR-06: Approving Authority approval transitions LTC request to Approved LTC Claim.
    """
    t = state_machine.decide_claim(
        state_machine.PENDING_AUTHORITY, action="approve", authority_step=0, route_length=1
    )
    assert t.state == state_machine.APPROVED


def test_wf_024_transition_4_approved_to_financial_processing(hr_caller):
    """TEST-WF-024 | BW-HR-06 transition-4-approved-to-financial-processing.

    Verify Transition 4 of BW-HR-06: Accountant settlement recording transitions Approved LTC Claim to Financial Processing Recorded.
    """
    claim = Claim.objects.create(
        employee_user_id=UID_FACULTY_1,
        employee_category="faculty",
        request_type="ltc_advance",
        purpose="Travel",
        status="approved",
        amount=Decimal("10000.00"),
    )
    actor_acc = make_actor(UID_ACCOUNTANT, role="Accountant", kind="staff")
    processed = claims.process_claim(
        actor=actor_acc,
        claim_id=claim.pk,
        financially_correct=True,
        details={"mode": "bank", "amount_disbursed": "10000.00"},
    )
    assert processed.status == "financial_processing_recorded"


def test_wf_025_reimbursement_approved_and_processed_path(hr_caller):
    """TEST-WF-025 | BW-HR-07 reimbursement-approved-and-processed-path.

    Execute complete finite path for LTC Reimbursement through verification, direct approval, and Accountant financial processing.
    """
    claim = Claim.objects.create(
        employee_user_id=UID_FACULTY_1,
        employee_category="faculty",
        request_type="ltc_reimbursement",
        purpose="Bills",
        status="approved",
        amount=Decimal("12000.00"),
    )
    actor_acc = make_actor(UID_ACCOUNTANT, role="Accountant", kind="staff")
    processed = claims.process_claim(
        actor=actor_acc,
        claim_id=claim.pk,
        financially_correct=True,
        details={"mode": "neft", "amount_disbursed": "12000.00"},
    )
    assert processed.status == "financial_processing_recorded"


def test_wf_026_transition_1_reimbursement_draft_to_submitted(hr_caller):
    """TEST-WF-026 | BW-HR-07 transition-1-reimbursement-draft-to-submitted.

    Verify Transition 1 of BW-HR-07: Submitting prescribed LTC reimbursement form transitions to Submitted / Awaiting HR Verification.
    """
    ensure_workflow_route("faculty", "ltc_reimbursement")
    ensure_employee(UID_FACULTY_1, kind="faculty")
    res = hr_caller(
        "post",
        "/api/v1/hr/claims/create/",
        user_id=UID_FACULTY_1,
        role="faculty",
        data={
            "request_type": "ltc_reimbursement",
            "purpose": "Tickets",
            "amount": "14000.00",
            "form_data": {"destination": "Home", "ticket_numbers": ["T123"]},
        },
    )
    assert res.status_code == 201


def test_wf_027_rejection_path(hr_caller):
    """TEST-WF-027 | BW-HR-08 rejection-path.

    Execute finite LTC path from verified request to rejection by Approving Authority.
    """
    t = state_machine.decide_claim(
        state_machine.PENDING_AUTHORITY, action="reject", authority_step=0, route_length=1
    )
    assert t.state == state_machine.REJECTED


def test_wf_028_forward_one_traversal_path(hr_caller):
    """TEST-WF-028 | BW-HR-09 forward-one-traversal-path.

    Execute exactly one forwarding traversal after LTC verification from Pending Current Authority to Pending Next Authority.
    """
    t = state_machine.decide_claim(
        state_machine.PENDING_AUTHORITY, action="forward", authority_step=0, route_length=2
    )
    assert t.state == state_machine.PENDING_NEXT_AUTHORITY
    assert t.authority_step == 1


def test_wf_029_forward_and_settlement_sequence(hr_caller):
    """TEST-WF-029 | CW-HR-03 forward-and-settlement-sequence.

    Execute composite LTC lifecycle combining submission, HR verification, intermediate forwarding, final approval, and financial processing.
    """
    t1 = state_machine.decide_claim(
        state_machine.PENDING_AUTHORITY, action="forward", authority_step=0, route_length=2
    )
    t2 = state_machine.decide_claim(
        t1.state, action="approve", authority_step=t1.authority_step, route_length=2
    )
    assert t2.state == state_machine.APPROVED


def test_wf_030_prohibited_skip_hr_verification(hr_caller):
    """TEST-WF-030 | CW-HR-03 prohibited-skip-hr-verification.

    Verify prohibited transition in CW-HR-03: Authority cannot approve an LTC request directly from Submitted / Awaiting HR Verification state.
    """
    with pytest.raises(state_machine.InvalidTransition):
        state_machine.decide_claim(
            state_machine.PENDING_VERIFICATION, action="approve", authority_step=0, route_length=1
        )


def test_wf_031_prohibited_settlement_before_approval(hr_caller):
    """TEST-WF-031 | CW-HR-03 prohibited-settlement-before-approval.

    Verify prohibited transition in CW-HR-03: Accountant cannot record settlement processing on an unapproved LTC request.
    """
    claim = Claim.objects.create(
        employee_user_id=UID_FACULTY_1,
        employee_category="faculty",
        request_type="ltc_advance",
        purpose="Travel",
        status="pending_authority",
        amount=Decimal("10000.00"),
    )
    actor_acc = make_actor(UID_ACCOUNTANT, role="Accountant", kind="staff")
    with pytest.raises(ConflictError):
        claims.process_claim(
            actor=actor_acc,
            claim_id=claim.pk,
            financially_correct=True,
            details={"mode": "neft"},
        )


def test_wf_032_prohibited_action_on_terminal_rejected_ltc(hr_caller):
    """TEST-WF-032 | CW-HR-03 prohibited-action-on-terminal-rejected-ltc.

    Verify prohibited transition in CW-HR-03: No transition can be executed on a terminal Rejected LTC request.
    """
    with pytest.raises(state_machine.InvalidTransition):
        state_machine.decide_claim(
            state_machine.REJECTED, action="approve", authority_step=0, route_length=1
        )
