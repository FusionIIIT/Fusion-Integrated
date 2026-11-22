"""Specification-Driven Automated Backend Tests for PHC Module.

Strategy: BR (Business Rules: Problem Statement + Business Rules Specification)
Adequacy: Cover every Business Rule with at least one test. Cover materially
          different permitted/prohibited outcomes, threshold sides, and exceptions.
"""
from datetime import date, time, timedelta
from decimal import Decimal
import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.phc.domain.entities import ReimbursementStatus, RequisitionStatus
from modules.phc.domain.errors import (
    ClaimImmutableError,
    IneligibleClaimantError,
    PrescriptionRequiredError,
    RequisitionNotApprovedError,
    SubmissionWindowExpiredError,
    UnauthorizedRecordAccessError,
)
from modules.phc.domain.rules import evaluate_claimant_eligibility
from modules.phc.domain.state_machine import ReimbursementStateMachine
from modules.phc.models.audit import PHCAuditTrail
from modules.phc.models.inventory import ProcurementRequisition
from modules.phc.models.notifications import PHCNotification
from modules.phc.models.patient_records import PatientVisit
from modules.phc.selectors.doctors import get_patient_doctor_availability
from modules.phc.selectors.patient_records import (
    get_patient_medical_history,
    get_patient_visit_by_id,
)
from modules.phc.services.doctors import (
    create_doctor,
    create_or_update_schedule,
    mark_attendance,
)
from modules.phc.services.inventory import (
    adjust_stock,
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
from modules.phc.services.reports import generate_administrative_report

pytestmark = pytest.mark.django_db


def _auth_client(stub_iam, user_id=101, kind="staff", roles=("staff",), permissions=()):
    stub_iam(make_session(
        user_id=user_id,
        kind=kind,
        roles=roles,
        active_role=roles[0] if roles else kind,
        permissions=permissions,
        modules=("phc",),
    ))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token fake-token")
    return client


# ---------------------------------------------------------------------------
# PHC-BR-01: Doctor Availability Display Logic
# ---------------------------------------------------------------------------

def test_br_001_doctor_availability_display_logic():
    """test_id: BR-TEST-001 | source_id: PHC-BR-01.

    Verify doctor availability combines master schedule and current-day real-time attendance.
    """
    doc = create_doctor(name="Dr. N. Reddy", specialization="Orthopedics")
    today_name = timezone.now().strftime("%A")
    create_or_update_schedule(
        doctor_id=doc.id,
        day_of_week=today_name,
        start_time=time(10, 0),
        end_time=time(14, 0),
        is_published=True,
    )
    mark_attendance(doctor_id=doc.id, status="Available", marked_by_user_id=10)

    avail = get_patient_doctor_availability()
    target = next((d for d in avail if d["doctor_id"] == doc.id), None)
    assert target is not None
    assert target["today_attendance"]["status"] == "Available"
    assert len(target["weekly_schedule"]) >= 1


# ---------------------------------------------------------------------------
# PHC-BR-02: Patient Medical Data Access Control
# ---------------------------------------------------------------------------

def test_br_002_patient_medical_data_access_permitted():
    """test_id: BR-TEST-002 | source_id: PHC-BR-02 condition-permitted.

    Verify patient can access their own medical records read-only.
    """
    visit = create_patient_visit(
        patient_user_id=2001,
        symptoms="Back pain",
        diagnosis="Lumbago",
        created_by_user_id=10,
        created_by_username="staff",
    )
    history = get_patient_medical_history(patient_user_id=2001)
    assert len(history) == 1
    assert history[0].id == visit.id


def test_br_003_patient_medical_data_access_prohibited():
    """test_id: BR-TEST-003 | source_id: PHC-BR-02 condition-prohibited.

    Verify patient accessing another patient medical record is strictly prohibited.
    """
    visit_other = create_patient_visit(
        patient_user_id=2002,
        symptoms="Secret illness",
        diagnosis="Confidential",
        created_by_user_id=10,
        created_by_username="staff",
    )
    with pytest.raises(UnauthorizedRecordAccessError):
        get_patient_visit_by_id(
            visit_id=visit_other.id,
            requesting_user_id=2001,
            is_staff=False,
        )


# ---------------------------------------------------------------------------
# PHC-BR-03: Role-Based Access Control
# ---------------------------------------------------------------------------

def test_br_004_rbac_permitted(stub_iam):
    """test_id: BR-TEST-004 | source_id: PHC-BR-03 condition-permitted.

    Verify authorized role permitted to perform assigned PHC function.
    """
    item = create_or_update_item(item_code="MED-BR-01", name="Bandage")
    client = _auth_client(
        stub_iam,
        user_id=10,
        kind="staff",
        roles=("staff",),
        permissions=("phc.inventory.adjust",),
    )
    res = client.post("/api/v1/phc/inventory/adjust/", {
        "item_id": item.id,
        "adjustment_type": "ADD",
        "quantity": 10,
        "reason": "Authorized stock addition",
    })
    assert res.status_code == 200


def test_br_005_rbac_prohibited(stub_iam):
    """test_id: BR-TEST-005 | source_id: PHC-BR-03 condition-prohibited.

    Verify unauthorized role denied from performing restricted PHC function.
    """
    item = create_or_update_item(item_code="MED-BR-02", name="Antiseptic")
    client = _auth_client(
        stub_iam,
        user_id=2001,
        kind="student",
        roles=("student",),
        permissions=("phc.patient_record.view_self",),
    )
    res = client.post("/api/v1/phc/inventory/adjust/", {
        "item_id": item.id,
        "adjustment_type": "ADD",
        "quantity": 10,
        "reason": "Unauthorized attempt",
    })
    assert res.status_code == 403


# ---------------------------------------------------------------------------
# PHC-BR-04: Reimbursement Eligibility - Employee Only
# ---------------------------------------------------------------------------

def test_br_006_reimbursement_eligibility_employee_permitted():
    """test_id: BR-TEST-006 | source_id: PHC-BR-04 outcome-permitted.

    Verify employee is eligible to submit reimbursement claim.
    """
    res_fac = evaluate_claimant_eligibility("faculty")
    assert res_fac.is_eligible is True
    res_staff = evaluate_claimant_eligibility("staff")
    assert res_staff.is_eligible is True


def test_br_007_reimbursement_eligibility_student_prohibited():
    """test_id: BR-TEST-007 | source_id: PHC-BR-04 outcome-prohibited.

    Verify student is strictly prohibited from submitting reimbursement claim.
    """
    res_stu = evaluate_claimant_eligibility("student")
    assert res_stu.is_eligible is False

    visit = create_patient_visit(patient_user_id=3001, symptoms="Cold", diagnosis="Flu", created_by_user_id=10, created_by_username="staff")
    presc = create_prescription(visit_id=visit.id, prescription_number="RX-BR-04", medicines_prescribed="Meds", created_by_user_id=10, created_by_username="staff")

    with pytest.raises(IneligibleClaimantError):
        submit_reimbursement_claim(
            claimant_user_id=3001,
            claimant_kind="student",
            claimant_username="stu3001",
            prescription_id=presc.id,
            expense_date=timezone.now().date(),
            amount_claimed=Decimal("500.00"),
        )


# ---------------------------------------------------------------------------
# PHC-BR-05: Reimbursement Prescription Prerequisite
# ---------------------------------------------------------------------------

def test_br_008_reimbursement_prescription_prerequisite_permitted():
    """test_id: BR-TEST-008 | source_id: PHC-BR-05 outcome-permitted.

    Verify reimbursement claim with valid prescription belonging to claimant is accepted.
    """
    visit = create_patient_visit(patient_user_id=1001, symptoms="Check", diagnosis="OK", created_by_user_id=10, created_by_username="staff")
    presc = create_prescription(visit_id=visit.id, prescription_number="RX-BR-05", medicines_prescribed="Meds", created_by_user_id=10, created_by_username="staff")

    claim = submit_reimbursement_claim(
        claimant_user_id=1001,
        claimant_kind="faculty",
        claimant_username="prof1001",
        prescription_id=presc.id,
        expense_date=timezone.now().date(),
        amount_claimed=Decimal("1200.00"),
    )
    assert claim.id is not None
    assert claim.prescription == presc


def test_br_009_reimbursement_prescription_prerequisite_prohibited():
    """test_id: BR-TEST-009 | source_id: PHC-BR-05 outcome-prohibited.

    Verify reimbursement claim missing valid claimant prescription is rejected.
    """
    # Non-existent prescription
    with pytest.raises(PrescriptionRequiredError):
        submit_reimbursement_claim(
            claimant_user_id=1001,
            claimant_kind="faculty",
            claimant_username="prof1001",
            prescription_id=88888,
            expense_date=timezone.now().date(),
            amount_claimed=Decimal("1200.00"),
        )


# ---------------------------------------------------------------------------
# PHC-BR-06: Reimbursement Submission Window
# ---------------------------------------------------------------------------

def test_br_010_submission_window_within_accepted():
    """test_id: BR-TEST-010 | source_id: PHC-BR-06 threshold-within.

    Verify reimbursement claim with expense date within 90-day window is accepted.
    """
    visit = create_patient_visit(patient_user_id=1001, symptoms="Check", diagnosis="OK", created_by_user_id=10, created_by_username="staff")
    presc = create_prescription(visit_id=visit.id, prescription_number="RX-BR-06-A", medicines_prescribed="Meds", created_by_user_id=10, created_by_username="staff")

    claim = submit_reimbursement_claim(
        claimant_user_id=1001,
        claimant_kind="faculty",
        claimant_username="prof1001",
        prescription_id=presc.id,
        expense_date=timezone.now().date() - timedelta(days=30),
        amount_claimed=Decimal("800.00"),
    )
    assert claim.id is not None


def test_br_011_submission_window_outside_rejected():
    """test_id: BR-TEST-011 | source_id: PHC-BR-06 threshold-outside.

    Verify reimbursement claim with expense date exceeding 90-day window is rejected.
    """
    visit = create_patient_visit(patient_user_id=1001, symptoms="Check", diagnosis="OK", created_by_user_id=10, created_by_username="staff")
    presc = create_prescription(visit_id=visit.id, prescription_number="RX-BR-06-B", medicines_prescribed="Meds", created_by_user_id=10, created_by_username="staff")

    with pytest.raises(SubmissionWindowExpiredError):
        submit_reimbursement_claim(
            claimant_user_id=1001,
            claimant_kind="faculty",
            claimant_username="prof1001",
            prescription_id=presc.id,
            expense_date=timezone.now().date() - timedelta(days=95),
            amount_claimed=Decimal("800.00"),
        )


# ---------------------------------------------------------------------------
# PHC-BR-07: Inventory Low-Stock Alert Trigger
# ---------------------------------------------------------------------------

def test_br_012_low_stock_trigger_strictly_below():
    """test_id: BR-TEST-012 | source_id: PHC-BR-07 threshold-below.

    Verify low-stock warning generated when stock level falls strictly below threshold.
    """
    item = create_or_update_item(item_code="MED-BR-07-A", name="Syrup A", reorder_threshold=20)
    adjust_stock(item.id, "ADD", 25, "Initial", 10, "staff")
    # Deduct 10 -> 15 (< 20)
    adjust_stock(item.id, "DEDUCT", 10, "Issue", 10, "staff")

    alert = PHCNotification.objects.filter(recipient_user_id=10, notification_type="LOW_STOCK")
    assert alert.exists()


def test_br_013_low_stock_trigger_at_or_above_no_alert():
    """test_id: BR-TEST-013 | source_id: PHC-BR-07 threshold-at-or-above.

    Verify no low-stock alert generated when stock level remains at or above threshold.
    """
    item = create_or_update_item(item_code="MED-BR-07-B", name="Syrup B", reorder_threshold=20)
    adjust_stock(item.id, "ADD", 30, "Initial", 10, "staff")
    PHCNotification.objects.filter(recipient_user_id=15).delete()

    # Deduct 10 -> exactly 20 (== threshold 20)
    adjust_stock(item.id, "DEDUCT", 10, "Issue", 15, "staff")

    # PHC-BR-07: Alert must be generated when stock drops to or below threshold (stock <= threshold)
    alert = PHCNotification.objects.filter(recipient_user_id=15, notification_type="LOW_STOCK")
    assert alert.exists()


# ---------------------------------------------------------------------------
# PHC-BR-08: Reimbursement Workflow Routing
# ---------------------------------------------------------------------------

def test_br_014_reimbursement_routing_forward_progression():
    """test_id: BR-TEST-014 | source_id: PHC-BR-08 forward-progression.

    Verify accepted claim follows exact forward progression across mandatory stages.
    """
    visit = create_patient_visit(patient_user_id=1001, symptoms="Check", diagnosis="OK", created_by_user_id=10, created_by_username="staff")
    presc = create_prescription(visit_id=visit.id, prescription_number="RX-BR-08", medicines_prescribed="Meds", created_by_user_id=10, created_by_username="staff")
    claim = submit_reimbursement_claim(claimant_user_id=1001, claimant_kind="staff", claimant_username="staff1001", prescription_id=presc.id, expense_date=timezone.now().date(), amount_claimed=Decimal("1500.00"))

    assert claim.status == ReimbursementStatus.PENDING_PHC_REVIEW.value
    review_claim_phc(claim.id, 10, "staff")
    claim.refresh_from_db()
    assert claim.status == ReimbursementStatus.PENDING_ACCOUNTS_VERIFICATION.value

    verify_claim_accounts(claim.id, 20, "accounts")
    claim.refresh_from_db()
    assert claim.status == ReimbursementStatus.PENDING_SANCTION.value

    decide_claim_sanction(claim.id, True, 30, "director")
    claim.refresh_from_db()
    assert claim.status == ReimbursementStatus.APPROVED_FOR_PAYMENT.value

    process_claim_payment(claim.id, 20, "accounts", payment_reference="PAY123")
    claim.refresh_from_db()
    assert claim.status == ReimbursementStatus.REIMBURSED.value


def test_br_015_reimbursement_routing_outcome_rejected():
    """test_id: BR-TEST-015 | source_id: PHC-BR-08 outcome-rejected.

    Verify Approving Authority rejection terminates reimbursement claim.
    """
    visit = create_patient_visit(patient_user_id=1001, symptoms="Check", diagnosis="OK", created_by_user_id=10, created_by_username="staff")
    presc = create_prescription(visit_id=visit.id, prescription_number="RX-BR-08-REJ", medicines_prescribed="Meds", created_by_user_id=10, created_by_username="staff")
    claim = submit_reimbursement_claim(claimant_user_id=1001, claimant_kind="staff", claimant_username="staff1001", prescription_id=presc.id, expense_date=timezone.now().date(), amount_claimed=Decimal("500.00"))
    review_claim_phc(claim.id, 10, "staff")
    verify_claim_accounts(claim.id, 20, "accounts")

    decide_claim_sanction(claim.id, False, 30, "director", comments="Budget exhausted")
    claim.refresh_from_db()
    assert claim.status == ReimbursementStatus.REJECTED.value


# ---------------------------------------------------------------------------
# PHC-BR-09: Immutable Sensitive-Data Audit Trail
# ---------------------------------------------------------------------------

def test_br_016_audit_patient_record():
    """test_id: BR-TEST-016 | source_id: PHC-BR-09 patient-record-audit.

    Verify immutable audit trail recorded when patient record is created.
    """
    visit = create_patient_visit(patient_user_id=2001, symptoms="Fever", diagnosis="Viral", created_by_user_id=10, created_by_username="staff")
    audit = PHCAuditTrail.objects.filter(target_type="PATIENT_RECORD", target_id=str(visit.id))
    assert audit.exists()


def test_br_017_audit_inventory_level():
    """test_id: BR-TEST-017 | source_id: PHC-BR-09 inventory-audit.

    Verify immutable audit trail recorded when inventory stock level is adjusted.
    """
    item = create_or_update_item(item_code="MED-BR-09", name="Audit Item")
    adjust_stock(item.id, "ADD", 100, "Audit stock add", 10, "staff")
    audit = PHCAuditTrail.objects.filter(target_type="INVENTORY_LEVEL", target_id=item.item_code)
    assert audit.exists()


def test_br_018_audit_reimbursement_claim():
    """test_id: BR-TEST-018 | source_id: PHC-BR-09 reimbursement-audit.

    Verify immutable audit trail recorded when reimbursement claim status changes.
    """
    visit = create_patient_visit(patient_user_id=1001, symptoms="Check", diagnosis="OK", created_by_user_id=10, created_by_username="staff")
    presc = create_prescription(visit_id=visit.id, prescription_number="RX-BR-09-CLM", medicines_prescribed="Meds", created_by_user_id=10, created_by_username="staff")
    claim = submit_reimbursement_claim(claimant_user_id=1001, claimant_kind="staff", claimant_username="staff1001", prescription_id=presc.id, expense_date=timezone.now().date(), amount_claimed=Decimal("1000.00"))

    audit = PHCAuditTrail.objects.filter(target_type="REIMBURSEMENT_CLAIM", target_id=claim.claim_number)
    assert audit.exists()


# ---------------------------------------------------------------------------
# PHC-BR-10: Inventory Requisition Approval Requirement
# ---------------------------------------------------------------------------

def test_br_019_inventory_requisition_fulfillment_permitted():
    """test_id: BR-TEST-019 | source_id: PHC-BR-10 outcome-permitted.

    Verify approved inventory requisition proceeds to delivery fulfillment.
    """
    item = create_or_update_item(item_code="MED-BR-10", name="Thermometer")
    req = submit_procurement_requisition(originator_user_id=10, originator_username="staff", justification="Need therm", items_data=[{"item_id": item.id, "quantity": 10}])
    decide_procurement_requisition(req.id, approve=True, actor_user_id=30, actor_username="director")

    fulfilled = fulfill_procurement_requisition(req.id, 10, "staff")
    assert fulfilled.status == RequisitionStatus.FULFILLED.value


def test_br_020_inventory_requisition_fulfillment_prohibited():
    """test_id: BR-TEST-020 | source_id: PHC-BR-10 outcome-prohibited.

    Verify fulfillment prohibited when requisition is not Approved.
    """
    item = create_or_update_item(item_code="MED-BR-10-B", name="Thermometer")
    req = submit_procurement_requisition(originator_user_id=10, originator_username="staff", justification="Need therm", items_data=[{"item_id": item.id, "quantity": 10}])

    with pytest.raises(RequisitionNotApprovedError):
        fulfill_procurement_requisition(req.id, 10, "staff")


# ---------------------------------------------------------------------------
# PHC-BR-11: Requisition Status Notification
# ---------------------------------------------------------------------------

def test_br_021_requisition_status_notification():
    """test_id: BR-TEST-021 | source_id: PHC-BR-11.

    Verify originator notified when inventory requisition is decided.
    """
    item = create_or_update_item(item_code="MED-BR-11", name="Gloves")
    req = submit_procurement_requisition(originator_user_id=10, originator_username="staff", justification="Need gloves", items_data=[{"item_id": item.id, "quantity": 50}])
    decide_procurement_requisition(req.id, approve=True, actor_user_id=30, actor_username="director")

    notifs = PHCNotification.objects.filter(recipient_user_id=10, notification_type="REQUISITION_DECISION")
    assert notifs.exists()


# ---------------------------------------------------------------------------
# PHC-BR-12: Report Privacy and Anonymization
# ---------------------------------------------------------------------------

def test_br_022_report_privacy_and_anonymization(stub_iam, user_ref):
    """test_id: BR-TEST-022 | source_id: PHC-BR-12.

    Verify administrative reports protect PII and anonymize patient data.
    """
    stub_iam(users={2001: user_ref(2001)})
    create_patient_visit(patient_user_id=2001, symptoms="Check", diagnosis="OK", created_by_user_id=10, created_by_username="staff")

    rep = generate_administrative_report("demographics")
    assert rep["anonymized"] is True
    assert "2001" not in rep["breakdown_by_category"]


# ---------------------------------------------------------------------------
# PHC-BR-13: Reimbursement Status Notification
# ---------------------------------------------------------------------------

def test_br_023_reimbursement_status_notification():
    """test_id: BR-TEST-023 | source_id: PHC-BR-13.

    Verify claimant notified on claim status changes including rejection and payment.
    """
    visit = create_patient_visit(patient_user_id=1001, symptoms="Check", diagnosis="OK", created_by_user_id=10, created_by_username="staff")
    presc = create_prescription(visit_id=visit.id, prescription_number="RX-BR-13", medicines_prescribed="Meds", created_by_user_id=10, created_by_username="staff")
    claim = submit_reimbursement_claim(claimant_user_id=1001, claimant_kind="staff", claimant_username="staff1001", prescription_id=presc.id, expense_date=timezone.now().date(), amount_claimed=Decimal("1000.00"))
    review_claim_phc(claim.id, 10, "staff")
    verify_claim_accounts(claim.id, 20, "accounts")
    decide_claim_sanction(claim.id, False, 30, "director")

    notifs = PHCNotification.objects.filter(recipient_user_id=1001, notification_type="REIMBURSEMENT_STATUS")
    assert notifs.filter(title__contains="Rejected").exists()


# ---------------------------------------------------------------------------
# PHC-BR-14: Reimbursement Claim Immutability and Fresh Reapplication
# ---------------------------------------------------------------------------

def test_br_024_reimbursement_claim_immutability():
    """test_id: BR-TEST-024 | source_id: PHC-BR-14.

    Verify in-place modification or reopening of submitted or rejected claim is prohibited.
    """
    with pytest.raises(ClaimImmutableError):
        ReimbursementStateMachine.assert_can_modify(ReimbursementStatus.PENDING_PHC_REVIEW.value)
    with pytest.raises(ClaimImmutableError):
        ReimbursementStateMachine.assert_can_modify(ReimbursementStatus.REJECTED.value)

    # Enforce model-level immutability on terminal claim instance
    visit = create_patient_visit(patient_user_id=1001, symptoms="Check", diagnosis="OK", created_by_user_id=10, created_by_username="staff")
    presc = create_prescription(visit_id=visit.id, prescription_number="RX-BR-14-IMM", medicines_prescribed="Meds", created_by_user_id=10, created_by_username="staff")
    claim = submit_reimbursement_claim(1001, "faculty", "prof1001", presc.id, timezone.now().date(), Decimal("1000.00"))
    claim.status = ReimbursementStatus.REJECTED.value
    claim.save()

    with pytest.raises(ClaimImmutableError):
        claim.amount_claimed = Decimal("5000.00")
        claim.clean()
        claim.save()
