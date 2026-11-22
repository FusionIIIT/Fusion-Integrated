"""Specification-Driven Automated Backend Tests for PHC Module.

Strategy: WF (Workflows: Problem Statement + Workflows Specification)
Adequacy: Cover every explicitly specified distinct workflow path / decision outcome.
          Ensure every important stated transition is exercised at least once.
"""
from datetime import date, timedelta
from decimal import Decimal
import pytest
from django.utils import timezone

from modules.phc.domain.entities import ReimbursementStatus, RequisitionStatus
from modules.phc.domain.errors import (
    ClaimImmutableError,
    InvalidStateTransitionError,
    RequisitionNotApprovedError,
)
from modules.phc.domain.state_machine import (
    ReimbursementStateMachine,
    RequisitionStateMachine,
)
from modules.phc.models.inventory import ProcurementRequisition
from modules.phc.models.notifications import PHCNotification
from modules.phc.models.reimbursement import ReimbursementClaim
from modules.phc.services.inventory import (
    create_or_update_item,
    decide_procurement_requisition,
    fulfill_procurement_requisition,
    submit_procurement_requisition,
)
from modules.phc.services.patient_records import create_patient_visit, create_prescription
from modules.phc.services.reimbursement import (
    decide_claim_sanction,
    process_claim_payment,
    review_claim_phc,
    submit_reimbursement_claim,
    verify_claim_accounts,
)

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# Reimbursement Workflows: BW-PHC-01, BW-PHC-02, CW-PHC-01
# ---------------------------------------------------------------------------

def test_wf_001_reimbursement_complete_success_path():
    """test_id: WF-TEST-001 | source_id: BW-PHC-01 Complete Success Path.

    Verify complete end-to-end reimbursement approval and reimbursement lifecycle.
    """
    visit = create_patient_visit(patient_user_id=1001, symptoms="Check", diagnosis="OK", created_by_user_id=10, created_by_username="staff")
    presc = create_prescription(visit_id=visit.id, prescription_number="RX-WF-001", medicines_prescribed="Meds", created_by_user_id=10, created_by_username="staff")

    # Step 1: Submit
    claim = submit_reimbursement_claim(1001, "faculty", "prof1001", presc.id, timezone.now().date(), Decimal("2000.00"))
    assert claim.status == ReimbursementStatus.PENDING_PHC_REVIEW.value

    # Step 2: PHC Review
    claim = review_claim_phc(claim.id, 10, "staff")
    assert claim.status == ReimbursementStatus.PENDING_ACCOUNTS_VERIFICATION.value

    # Step 3: Accounts Verify
    claim = verify_claim_accounts(claim.id, 20, "accounts", amount_verified=Decimal("2000.00"))
    assert claim.status == ReimbursementStatus.PENDING_SANCTION.value

    # Step 4: Sanction Approve
    claim = decide_claim_sanction(claim.id, True, 30, "director")
    assert claim.status == ReimbursementStatus.APPROVED_FOR_PAYMENT.value

    # Step 5: Payment Process
    claim = process_claim_payment(claim.id, 20, "accounts", payment_reference="PAY-WF-1")
    assert claim.status == ReimbursementStatus.REIMBURSED.value


def test_wf_002_reimbursement_trans_draft_to_pending_phc():
    """test_id: WF-TEST-002 | source_id: BW-PHC-01 Transition Draft to Pending PHC Review.

    Verify transition from Draft to Pending PHC Review upon employee submission.
    """
    visit = create_patient_visit(patient_user_id=1001, symptoms="Check", diagnosis="OK", created_by_user_id=10, created_by_username="staff")
    presc = create_prescription(visit_id=visit.id, prescription_number="RX-WF-002", medicines_prescribed="Meds", created_by_user_id=10, created_by_username="staff")
    claim = submit_reimbursement_claim(1001, "faculty", "prof1001", presc.id, timezone.now().date(), Decimal("1000.00"))
    assert claim.status == ReimbursementStatus.PENDING_PHC_REVIEW.value
    assert claim.history.filter(action="SUBMIT_CLAIM").exists()


def test_wf_003_reimbursement_trans_phc_to_accounts():
    """test_id: WF-TEST-003 | source_id: BW-PHC-01 Transition Pending PHC Review to Pending Accounts Verification.

    Verify transition from Pending PHC Review to Pending Accounts Verification.
    """
    visit = create_patient_visit(patient_user_id=1001, symptoms="Check", diagnosis="OK", created_by_user_id=10, created_by_username="staff")
    presc = create_prescription(visit_id=visit.id, prescription_number="RX-WF-003", medicines_prescribed="Meds", created_by_user_id=10, created_by_username="staff")
    claim = submit_reimbursement_claim(1001, "faculty", "prof1001", presc.id, timezone.now().date(), Decimal("1000.00"))

    claim = review_claim_phc(claim.id, 10, "staff")
    assert claim.status == ReimbursementStatus.PENDING_ACCOUNTS_VERIFICATION.value


def test_wf_004_reimbursement_trans_accounts_to_sanction():
    """test_id: WF-TEST-004 | source_id: BW-PHC-01 Transition Pending Accounts Verification to Pending Sanction.

    Verify transition from Pending Accounts Verification to Pending Sanction.
    """
    visit = create_patient_visit(patient_user_id=1001, symptoms="Check", diagnosis="OK", created_by_user_id=10, created_by_username="staff")
    presc = create_prescription(visit_id=visit.id, prescription_number="RX-WF-004", medicines_prescribed="Meds", created_by_user_id=10, created_by_username="staff")
    claim = submit_reimbursement_claim(1001, "faculty", "prof1001", presc.id, timezone.now().date(), Decimal("1000.00"))
    review_claim_phc(claim.id, 10, "staff")

    claim = verify_claim_accounts(claim.id, 20, "accounts")
    assert claim.status == ReimbursementStatus.PENDING_SANCTION.value


def test_wf_005_reimbursement_trans_sanction_to_approved():
    """test_id: WF-TEST-005 | source_id: BW-PHC-01 Transition Pending Sanction to Approved for Payment.

    Verify transition from Pending Sanction to Approved for Payment on approval.
    """
    visit = create_patient_visit(patient_user_id=1001, symptoms="Check", diagnosis="OK", created_by_user_id=10, created_by_username="staff")
    presc = create_prescription(visit_id=visit.id, prescription_number="RX-WF-005", medicines_prescribed="Meds", created_by_user_id=10, created_by_username="staff")
    claim = submit_reimbursement_claim(1001, "faculty", "prof1001", presc.id, timezone.now().date(), Decimal("1000.00"))
    review_claim_phc(claim.id, 10, "staff")
    verify_claim_accounts(claim.id, 20, "accounts")

    claim = decide_claim_sanction(claim.id, True, 30, "director")
    assert claim.status == ReimbursementStatus.APPROVED_FOR_PAYMENT.value


def test_wf_006_reimbursement_trans_approved_to_reimbursed():
    """test_id: WF-TEST-006 | source_id: BW-PHC-01 Transition Approved for Payment to Reimbursed.

    Verify transition from Approved for Payment to Reimbursed upon payment completion.
    """
    visit = create_patient_visit(patient_user_id=1001, symptoms="Check", diagnosis="OK", created_by_user_id=10, created_by_username="staff")
    presc = create_prescription(visit_id=visit.id, prescription_number="RX-WF-006", medicines_prescribed="Meds", created_by_user_id=10, created_by_username="staff")
    claim = submit_reimbursement_claim(1001, "faculty", "prof1001", presc.id, timezone.now().date(), Decimal("1000.00"))
    review_claim_phc(claim.id, 10, "staff")
    verify_claim_accounts(claim.id, 20, "accounts")
    decide_claim_sanction(claim.id, True, 30, "director")

    claim = process_claim_payment(claim.id, 20, "accounts", payment_reference="PAY-WF-6")
    assert claim.status == ReimbursementStatus.REIMBURSED.value


def test_wf_007_reimbursement_complete_rejection_path():
    """test_id: WF-TEST-007 | source_id: BW-PHC-02 Complete Rejection Path.

    Verify complete end-to-end reimbursement rejection lifecycle terminating at sanction.
    """
    visit = create_patient_visit(patient_user_id=1001, symptoms="Check", diagnosis="OK", created_by_user_id=10, created_by_username="staff")
    presc = create_prescription(visit_id=visit.id, prescription_number="RX-WF-007", medicines_prescribed="Meds", created_by_user_id=10, created_by_username="staff")
    claim = submit_reimbursement_claim(1001, "faculty", "prof1001", presc.id, timezone.now().date(), Decimal("1000.00"))
    review_claim_phc(claim.id, 10, "staff")
    verify_claim_accounts(claim.id, 20, "accounts")

    claim = decide_claim_sanction(claim.id, False, 30, "director", comments="Exceeds per-visit entitlement")
    assert claim.status == ReimbursementStatus.REJECTED.value


def test_wf_008_reimbursement_trans_sanction_to_rejected():
    """test_id: WF-TEST-008 | source_id: BW-PHC-02 Transition Pending Sanction to Rejected.

    Verify transition from Pending Sanction to Rejected on sanction denial.
    """
    visit = create_patient_visit(patient_user_id=1001, symptoms="Check", diagnosis="OK", created_by_user_id=10, created_by_username="staff")
    presc = create_prescription(visit_id=visit.id, prescription_number="RX-WF-008", medicines_prescribed="Meds", created_by_user_id=10, created_by_username="staff")
    claim = submit_reimbursement_claim(1001, "faculty", "prof1001", presc.id, timezone.now().date(), Decimal("1000.00"))
    review_claim_phc(claim.id, 10, "staff")
    verify_claim_accounts(claim.id, 20, "accounts")

    claim = decide_claim_sanction(claim.id, False, 30, "director")
    assert claim.status == ReimbursementStatus.REJECTED.value
    notif = PHCNotification.objects.filter(recipient_user_id=1001, notification_type="REIMBURSEMENT_STATUS")
    assert notif.filter(title__contains="Rejected").exists()


def test_wf_009_reimbursement_out_of_order_transition_blocked():
    """test_id: WF-TEST-009 | source_id: CW-PHC-01 Out-of-Order Transition Blocked.

    Verify out-of-order state transition is strictly prevented in reimbursement progression.
    """
    visit = create_patient_visit(patient_user_id=1001, symptoms="Check", diagnosis="OK", created_by_user_id=10, created_by_username="staff")
    presc = create_prescription(visit_id=visit.id, prescription_number="RX-WF-009", medicines_prescribed="Meds", created_by_user_id=10, created_by_username="staff")
    claim = submit_reimbursement_claim(1001, "faculty", "prof1001", presc.id, timezone.now().date(), Decimal("1000.00"))

    # Attempt to skip review and go straight to verification or sanction
    with pytest.raises(InvalidStateTransitionError):
        verify_claim_accounts(claim.id, 20, "accounts")
    with pytest.raises(InvalidStateTransitionError):
        decide_claim_sanction(claim.id, True, 30, "director")
    with pytest.raises(InvalidStateTransitionError):
        process_claim_payment(claim.id, 20, "accounts")


def test_wf_010_reimbursement_terminal_state_immutable():
    """test_id: WF-TEST-010 | source_id: CW-PHC-01 Terminal State Immutable.

    Verify reimbursement claim in terminal state Reimbursed or Rejected cannot transition further.
    """
    visit = create_patient_visit(patient_user_id=1001, symptoms="Check", diagnosis="OK", created_by_user_id=10, created_by_username="staff")
    presc = create_prescription(visit_id=visit.id, prescription_number="RX-WF-010", medicines_prescribed="Meds", created_by_user_id=10, created_by_username="staff")
    claim = submit_reimbursement_claim(1001, "faculty", "prof1001", presc.id, timezone.now().date(), Decimal("1000.00"))
    claim = review_claim_phc(claim.id, 10, "staff")
    claim = verify_claim_accounts(claim.id, 20, "accounts")
    claim = decide_claim_sanction(claim.id, False, 30, "director")
    assert claim.status == ReimbursementStatus.REJECTED.value

    # Attempting any action on terminal state raises error
    with pytest.raises(InvalidStateTransitionError):
        decide_claim_sanction(claim.id, True, 30, "director")
    with pytest.raises(InvalidStateTransitionError):
        process_claim_payment(claim.id, 20, "accounts")
    with pytest.raises(ClaimImmutableError):
        ReimbursementStateMachine.assert_can_modify(claim.status)

    # Terminal claim is immutable: modifying and saving must raise ClaimImmutableError per BR-14
    with pytest.raises(ClaimImmutableError):
        claim.amount_claimed = Decimal("2000.00")
        claim.clean()
        claim.save()


# ---------------------------------------------------------------------------
# Procurement Requisition Workflows: BW-PHC-03, BW-PHC-04, CW-PHC-02
# ---------------------------------------------------------------------------

def test_wf_011_requisition_complete_success_path():
    """test_id: WF-TEST-011 | source_id: BW-PHC-03 Complete Success Path.

    Verify complete end-to-end inventory requisition approval and fulfillment lifecycle.
    """
    item = create_or_update_item(item_code="MED-WF-01", name="IV Drip")
    # Step 1: Submit
    req = submit_procurement_requisition(10, "staff", "Emergency stock", [{"item_id": item.id, "quantity": 100}])
    assert req.status == RequisitionStatus.PENDING_APPROVAL.value

    # Step 2: Approve
    req = decide_procurement_requisition(req.id, True, 30, "director")
    assert req.status == RequisitionStatus.APPROVED.value

    # Step 3: Fulfill
    req = fulfill_procurement_requisition(req.id, 10, "staff")
    assert req.status == RequisitionStatus.FULFILLED.value


def test_wf_012_requisition_trans_draft_to_pending():
    """test_id: WF-TEST-012 | source_id: BW-PHC-03 Transition Draft to Pending Approval.

    Verify transition from Draft to Pending Approval on staff submission.
    """
    item = create_or_update_item(item_code="MED-WF-02", name="Syringe")
    req = submit_procurement_requisition(10, "staff", "Need syringes", [{"item_id": item.id, "quantity": 50}])
    assert req.status == RequisitionStatus.PENDING_APPROVAL.value


def test_wf_013_requisition_trans_pending_to_approved():
    """test_id: WF-TEST-013 | source_id: BW-PHC-03 Transition Pending Approval to Approved.

    Verify transition from Pending Approval to Approved on authority approval.
    """
    item = create_or_update_item(item_code="MED-WF-03", name="Needles")
    req = submit_procurement_requisition(10, "staff", "Need needles", [{"item_id": item.id, "quantity": 50}])

    req = decide_procurement_requisition(req.id, True, 30, "director")
    assert req.status == RequisitionStatus.APPROVED.value


def test_wf_014_requisition_trans_approved_to_fulfilled():
    """test_id: WF-TEST-014 | source_id: BW-PHC-03 Transition Approved to Fulfilled.

    Verify transition from Approved to Fulfilled after supply delivery.
    """
    item = create_or_update_item(item_code="MED-WF-04", name="Gauze")
    req = submit_procurement_requisition(10, "staff", "Need gauze", [{"item_id": item.id, "quantity": 50}])
    decide_procurement_requisition(req.id, True, 30, "director")

    req = fulfill_procurement_requisition(req.id, 10, "staff")
    assert req.status == RequisitionStatus.FULFILLED.value


def test_wf_015_requisition_complete_rejection_path():
    """test_id: WF-TEST-015 | source_id: BW-PHC-04 Complete Rejection Path.

    Verify complete end-to-end inventory requisition rejection lifecycle.
    """
    item = create_or_update_item(item_code="MED-WF-05", name="Expensive Scanner")
    req = submit_procurement_requisition(10, "staff", "Scanner", [{"item_id": item.id, "quantity": 1}])
    req = decide_procurement_requisition(req.id, False, 30, "director", remarks="Not in annual budget")
    assert req.status == RequisitionStatus.REJECTED.value


def test_wf_016_requisition_trans_pending_to_rejected():
    """test_id: WF-TEST-016 | source_id: BW-PHC-04 Transition Pending Approval to Rejected.

    Verify transition from Pending Approval to Rejected on authority rejection.
    """
    item = create_or_update_item(item_code="MED-WF-06", name="Reagent B")
    req = submit_procurement_requisition(10, "staff", "Reagent B", [{"item_id": item.id, "quantity": 2}])
    req = decide_procurement_requisition(req.id, False, 30, "director")
    assert req.status == RequisitionStatus.REJECTED.value
    notif = PHCNotification.objects.filter(recipient_user_id=10, notification_type="REQUISITION_DECISION")
    assert notif.filter(title__contains="Rejected").exists()


def test_wf_017_requisition_fulfillment_blocked_before_approval():
    """test_id: WF-TEST-017 | source_id: CW-PHC-02 Fulfillment Blocked Before Approval.

    Verify requisition cannot be marked Fulfilled prior to approval.
    """
    item = create_or_update_item(item_code="MED-WF-07", name="Bandage")
    req = submit_procurement_requisition(10, "staff", "Bandage", [{"item_id": item.id, "quantity": 20}])

    with pytest.raises(RequisitionNotApprovedError):
        fulfill_procurement_requisition(req.id, 10, "staff")


def test_wf_018_requisition_terminal_state_immutable():
    """test_id: WF-TEST-018 | source_id: CW-PHC-02 Terminal State Immutable.

    Verify requisition in terminal state Fulfilled or Rejected cannot be decided again.
    """
    item = create_or_update_item(item_code="MED-WF-08", name="Plaster")
    req = submit_procurement_requisition(10, "staff", "Plaster", [{"item_id": item.id, "quantity": 10}])
    req = decide_procurement_requisition(req.id, False, 30, "director")
    assert req.status == RequisitionStatus.REJECTED.value

    with pytest.raises(InvalidStateTransitionError):
        decide_procurement_requisition(req.id, True, 30, "director")
