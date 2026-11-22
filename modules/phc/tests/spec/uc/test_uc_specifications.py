"""Specification-Driven Automated Backend Tests for PHC Module.

Strategy: UC (Use Cases: Problem Statement + Use Cases Specification)
Adequacy: Cover the main success flow of every active Use Case and every
          explicitly specified alternative/exception flow.
"""
from datetime import date, datetime, time, timedelta
from decimal import Decimal
import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from conftest import make_session
from modules.phc.domain.entities import ReimbursementStatus, RequisitionStatus
from modules.phc.domain.errors import (
    IneligibleClaimantError,
    InsufficientStockError,
    InvalidStateTransitionError,
    PrescriptionRequiredError,
    RequisitionNotApprovedError,
    SubmissionWindowExpiredError,
    UnauthorizedRecordAccessError,
)
from modules.phc.models.ambulance import AmbulanceLog
from modules.phc.models.announcements import HealthAnnouncement
from modules.phc.models.doctors import Doctor, DoctorAttendance, DoctorSchedule
from modules.phc.models.inventory import InventoryItem, ProcurementRequisition
from modules.phc.models.notifications import PHCNotification
from modules.phc.models.patient_records import PatientVisit, Prescription
from modules.phc.models.reimbursement import ReimbursementClaim
from modules.phc.selectors.announcements import list_active_announcements
from modules.phc.selectors.doctors import get_patient_doctor_availability
from modules.phc.selectors.patient_records import (
    get_patient_medical_history,
    get_patient_prescriptions,
    get_patient_visit_by_id,
)
from modules.phc.selectors.reimbursement import get_user_reimbursement_claims
from modules.phc.services.ambulance import log_ambulance_usage
from modules.phc.services.announcements import publish_health_announcement
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
# PHC-UC-01: View Doctor Schedule & Availability
# ---------------------------------------------------------------------------

def test_uc_001_view_doctor_schedule_and_availability():
    """test_id: UC-TEST-001 | source_id: PHC-UC-01 Main Flow.

    Verify patient views static weekly schedule together with live attendance status.
    """
    doc = create_doctor(name="Dr. H. Mehta", specialization="Cardiology")
    today_name = timezone.now().strftime("%A")
    create_or_update_schedule(
        doctor_id=doc.id,
        day_of_week=today_name,
        start_time=time(9, 0),
        end_time=time(13, 0),
        room_number="Room 101",
        is_published=True,
    )
    mark_attendance(doctor_id=doc.id, status="Available", marked_by_user_id=10)

    avail = get_patient_doctor_availability()
    target = next((d for d in avail if d["doctor_id"] == doc.id), None)
    assert target is not None
    assert target["today_attendance"]["status"] == "Available"
    assert len(target["weekly_schedule"]) >= 1


# ---------------------------------------------------------------------------
# PHC-UC-02: View Medical History & Prescriptions
# ---------------------------------------------------------------------------

def test_uc_002_view_medical_history_and_prescriptions():
    """test_id: UC-TEST-002 | source_id: PHC-UC-02 Main Flow.

    Verify patient views own medical history and prescriptions read-only.
    """
    visit = create_patient_visit(
        patient_user_id=2001,
        symptoms="Persistent dry cough",
        diagnosis="Acute Bronchitis",
        created_by_user_id=10,
        created_by_username="staff_user",
    )
    presc = create_prescription(
        visit_id=visit.id,
        prescription_number="RX-UC-001",
        medicines_prescribed="Cough syrup 10ml TDS",
        created_by_user_id=10,
        created_by_username="staff_user",
    )

    history = get_patient_medical_history(patient_user_id=2001)
    prescriptions = get_patient_prescriptions(patient_user_id=2001)

    assert len(history) == 1
    assert history[0].diagnosis == "Acute Bronchitis"
    assert len(prescriptions) == 1
    assert prescriptions[0].prescription_number == "RX-UC-001"


def test_uc_003_patient_access_to_other_record_denied():
    """test_id: UC-TEST-003 | source_id: PHC-UC-02 Exception E1.

    Verify access is denied when patient attempts to view another patient's records.
    """
    visit_other = create_patient_visit(
        patient_user_id=2002,
        symptoms="Private symptom",
        diagnosis="Confidential condition",
        created_by_user_id=10,
        created_by_username="staff_user",
    )
    # Patient 2001 queries visit of Patient 2002
    with pytest.raises(UnauthorizedRecordAccessError):
        get_patient_visit_by_id(
            visit_id=visit_other.id,
            requesting_user_id=2001,
            is_staff=False,
        )


# ---------------------------------------------------------------------------
# PHC-UC-03: Download Medical Records
# ---------------------------------------------------------------------------

def test_uc_004_download_medical_records_pdf(stub_iam):
    """test_id: UC-TEST-004 | source_id: PHC-UC-03 Main Flow.

    Verify patient downloads PDF copy of own medical records.
    """
    create_patient_visit(
        patient_user_id=2001,
        symptoms="Seasonal Allergy",
        diagnosis="Rhinitis",
        created_by_user_id=10,
        created_by_username="staff_user",
    )
    client = _auth_client(
        stub_iam,
        user_id=2001,
        kind="student",
        roles=("student",),
        permissions=("phc.patient_record.download_self",),
    )
    res = client.get("/api/v1/phc/patient/download/")
    assert res.status_code == 200
    assert res["Content-Type"] == "application/pdf"
    assert res.content.startswith(b"%PDF")


# ---------------------------------------------------------------------------
# PHC-UC-04: Apply for Medical Bill Reimbursement
# ---------------------------------------------------------------------------

def test_uc_005_apply_reimbursement_main_flow():
    """test_id: UC-TEST-005 | source_id: PHC-UC-04 Main Flow.

    Verify eligible employee applies for medical bill reimbursement successfully.
    """
    visit = create_patient_visit(patient_user_id=1001, symptoms="Checkup", diagnosis="OK", created_by_user_id=10, created_by_username="staff")
    presc = create_prescription(visit_id=visit.id, prescription_number="RX-UC-CLM-01", medicines_prescribed="Meds", created_by_user_id=10, created_by_username="staff")

    claim = submit_reimbursement_claim(
        claimant_user_id=1001,
        claimant_kind="faculty",
        claimant_username="prof1001",
        prescription_id=presc.id,
        expense_date=timezone.now().date() - timedelta(days=10),
        amount_claimed=Decimal("1800.00"),
        remarks="Specialist fee",
    )
    assert claim.id is not None
    assert claim.status == ReimbursementStatus.PENDING_PHC_REVIEW.value
    assert claim.history.filter(action="SUBMIT_CLAIM").exists()


def test_uc_006_apply_reimbursement_alt1_student_denied():
    """test_id: UC-TEST-006 | source_id: PHC-UC-04 Alternative A1.

    Verify reimbursement submission denied when user is not an employee (e.g. student).
    """
    visit = create_patient_visit(patient_user_id=3001, symptoms="Checkup", diagnosis="OK", created_by_user_id=10, created_by_username="staff")
    presc = create_prescription(visit_id=visit.id, prescription_number="RX-UC-CLM-02", medicines_prescribed="Meds", created_by_user_id=10, created_by_username="staff")

    with pytest.raises(IneligibleClaimantError):
        submit_reimbursement_claim(
            claimant_user_id=3001,
            claimant_kind="student",
            claimant_username="stu3001",
            prescription_id=presc.id,
            expense_date=timezone.now().date(),
            amount_claimed=Decimal("500.00"),
        )


def test_uc_007_apply_reimbursement_alt2_invalid_prescription():
    """test_id: UC-TEST-007 | source_id: PHC-UC-04 Alternative A2.

    Verify reimbursement submission denied when prescription is missing or not owned by claimant.
    """
    # Non-existent prescription
    with pytest.raises(PrescriptionRequiredError):
        submit_reimbursement_claim(
            claimant_user_id=1001,
            claimant_kind="faculty",
            claimant_username="prof1001",
            prescription_id=99999,
            expense_date=timezone.now().date(),
            amount_claimed=Decimal("700.00"),
        )


def test_uc_008_apply_reimbursement_alt3_expired_submission_window():
    """test_id: UC-TEST-008 | source_id: PHC-UC-04 Alternative A3.

    Verify reimbursement submission denied when expense date is outside submission window (>90 days).
    """
    visit = create_patient_visit(patient_user_id=1001, symptoms="Checkup", diagnosis="OK", created_by_user_id=10, created_by_username="staff")
    presc = create_prescription(visit_id=visit.id, prescription_number="RX-UC-CLM-03", medicines_prescribed="Meds", created_by_user_id=10, created_by_username="staff")

    expired_date = timezone.now().date() - timedelta(days=100)
    with pytest.raises(SubmissionWindowExpiredError):
        submit_reimbursement_claim(
            claimant_user_id=1001,
            claimant_kind="faculty",
            claimant_username="prof1001",
            prescription_id=presc.id,
            expense_date=expired_date,
            amount_claimed=Decimal("700.00"),
        )


# ---------------------------------------------------------------------------
# PHC-UC-05: Track Reimbursement Status
# ---------------------------------------------------------------------------

def test_uc_009_track_reimbursement_status():
    """test_id: UC-TEST-009 | source_id: PHC-UC-05 Main Flow.

    Verify employee tracks status and action history of own reimbursement claims.
    """
    visit = create_patient_visit(patient_user_id=1001, symptoms="Checkup", diagnosis="OK", created_by_user_id=10, created_by_username="staff")
    presc = create_prescription(visit_id=visit.id, prescription_number="RX-UC-CLM-04", medicines_prescribed="Meds", created_by_user_id=10, created_by_username="staff")
    claim = submit_reimbursement_claim(claimant_user_id=1001, claimant_kind="faculty", claimant_username="prof1001", prescription_id=presc.id, expense_date=timezone.now().date(), amount_claimed=Decimal("950.00"))
    review_claim_phc(claim.id, actor_user_id=10, actor_username="staff_user")

    claims = get_user_reimbursement_claims(claimant_user_id=1001)
    target = next((c for c in claims if c.id == claim.id), None)
    assert target is not None
    assert target.status == ReimbursementStatus.PENDING_ACCOUNTS_VERIFICATION.value
    assert target.history.count() == 2


# ---------------------------------------------------------------------------
# PHC-UC-06: Record Patient Visit & Prescription
# ---------------------------------------------------------------------------

def test_uc_010_record_patient_visit_and_prescription():
    """test_id: UC-TEST-010 | source_id: PHC-UC-06 Main Flow.

    Verify PHC Staff records patient visit and digitizes prescription.
    """
    visit = create_patient_visit(
        patient_user_id=2001,
        symptoms="Severe sore throat",
        diagnosis="Pharyngitis",
        created_by_user_id=10,
        created_by_username="nurse_staff",
    )
    presc = create_prescription(
        visit_id=visit.id,
        prescription_number="RX-UC-06-01",
        medicines_prescribed="Amoxicillin 500mg TDS x 5 days",
        created_by_user_id=10,
        created_by_username="nurse_staff",
    )
    assert visit.id is not None
    assert presc.id is not None
    assert presc.visit == visit


# ---------------------------------------------------------------------------
# PHC-UC-07: Maintain Doctor Master Schedule
# ---------------------------------------------------------------------------

def test_uc_011_maintain_doctor_master_schedule():
    """test_id: UC-TEST-011 | source_id: PHC-UC-07 Main Flow.

    Verify PHC Staff maintains doctor master schedule.
    """
    doc = create_doctor(name="Dr. K. Joshi", specialization="Ophthalmology")
    sched = create_or_update_schedule(
        doctor_id=doc.id,
        day_of_week="Monday",
        start_time=time(14, 0),
        end_time=time(17, 0),
        room_number="Room 301",
    )
    updated = create_or_update_schedule(
        doctor_id=doc.id,
        day_of_week="Friday",
        start_time=time(10, 0),
        end_time=time(13, 0),
        room_number="Room 305",
        schedule_id=sched.id,
    )
    assert updated.id == sched.id
    assert updated.day_of_week == "Friday"
    assert updated.room_number == "Room 305"


# ---------------------------------------------------------------------------
# PHC-UC-08: Mark Doctor Attendance
# ---------------------------------------------------------------------------

def test_uc_012_mark_doctor_attendance():
    """test_id: UC-TEST-012 | source_id: PHC-UC-08 Main Flow.

    Verify PHC Staff marks doctor real-time attendance.
    """
    doc = create_doctor(name="Dr. L. Roy", specialization="Psychiatry")
    att = mark_attendance(doctor_id=doc.id, status="Available", marked_by_user_id=10, remarks="In clinic")
    assert att.status == "Available"
    att_dep = mark_attendance(doctor_id=doc.id, status="Departed", marked_by_user_id=10, remarks="Session ended")
    assert att_dep.status == "Departed"

    # Exception flow: invalid/unsupported attendance status must raise ValueError
    with pytest.raises(ValueError):
        mark_attendance(doctor_id=doc.id, status="ON_VACATION", marked_by_user_id=10)


# ---------------------------------------------------------------------------
# PHC-UC-09: Manage Inventory Stock
# ---------------------------------------------------------------------------

def test_uc_013_manage_inventory_stock_low_stock_alert():
    """test_id: UC-TEST-013 | source_id: PHC-UC-09 Main Flow.

    Verify stock deduction below threshold triggers low-stock alert.
    """
    item = create_or_update_item(item_code="MED-UC-01", name="Betadine 100ml", reorder_threshold=15)
    adjust_stock(item.id, "ADD", 20, "Batch receipt", 10, "staff")
    # Deduct 10 -> remaining 10 (< 15)
    adjust_stock(item.id, "DEDUCT", 10, "Clinic use", 10, "staff")

    alert = PHCNotification.objects.filter(recipient_user_id=10, notification_type="LOW_STOCK")
    assert alert.exists()


def test_uc_014_manage_inventory_stock_alt1_no_alert():
    """test_id: UC-TEST-014 | source_id: PHC-UC-09 Alternative A1.

    Verify stock adjustment keeping level at or above threshold generates no alert.
    """
    item = create_or_update_item(item_code="MED-UC-02", name="Cotton Roll", reorder_threshold=10)
    adjust_stock(item.id, "ADD", 30, "Initial batch", 10, "staff")
    PHCNotification.objects.filter(recipient_user_id=12).delete()

    adjust_stock(item.id, "DEDUCT", 5, "Ward use", 12, "staff2")
    alert = PHCNotification.objects.filter(recipient_user_id=12, notification_type="LOW_STOCK")
    assert not alert.exists()


def test_uc_015_manage_inventory_stock_exc1_insufficient_stock():
    """test_id: UC-TEST-015 | source_id: PHC-UC-09 Exception E1.

    Verify stock adjustment rejecting deduction exceeding available stock.
    """
    item = create_or_update_item(item_code="MED-UC-03", name="Surgical Gloves", reorder_threshold=5)
    adjust_stock(item.id, "ADD", 5, "Initial", 10, "staff")

    with pytest.raises(InsufficientStockError):
        adjust_stock(item.id, "DEDUCT", 10, "Exceeding quantity", 10, "staff")


# ---------------------------------------------------------------------------
# PHC-UC-10: Submit Inventory Requisition
# ---------------------------------------------------------------------------

def test_uc_016_submit_inventory_requisition():
    """test_id: UC-TEST-016 | source_id: PHC-UC-10 Main Flow.

    Verify PHC Staff submits inventory procurement requisition.
    """
    item = create_or_update_item(item_code="MED-UC-REQ-01", name="Syringes 5ml")
    req = submit_procurement_requisition(
        originator_user_id=10,
        originator_username="staff_user",
        justification="Depleted emergency stock",
        items_data=[{"item_id": item.id, "quantity": 100}],
    )
    assert req.id is not None
    assert req.status == RequisitionStatus.PENDING_APPROVAL.value
    assert req.items.first().quantity_requested == 100


# ---------------------------------------------------------------------------
# PHC-UC-11: Log Ambulance Usage
# ---------------------------------------------------------------------------

def test_uc_017_log_ambulance_usage():
    """test_id: UC-TEST-017 | source_id: PHC-UC-11 Main Flow.

    Verify PHC Staff logs ambulance usage with required details.
    """
    dep = timezone.now()
    log = log_ambulance_usage(
        patient_name="Pooja Sharma",
        destination="Medical College Hospital",
        departure_time=dep,
        driver_name="Suresh Kumar",
        recorded_by_user_id=10,
        reason="Emergency surgery transfer",
    )
    assert log.id is not None
    assert log.driver_name == "Suresh Kumar"


def test_uc_018_log_ambulance_usage_missing_field(stub_iam):
    """test_id: UC-TEST-018 | source_id: PHC-UC-11 Exception E1.

    Verify ambulance log rejected when required field is missing.
    """
    client = _auth_client(stub_iam, user_id=10, permissions=("phc.ambulance.manage",))
    res = client.post("/api/v1/phc/ambulance/", {
        "patient_name": "Test Patient",
        # Missing destination and driver_name
    })
    assert res.status_code == 400


# ---------------------------------------------------------------------------
# PHC-UC-12: Broadcast Health Announcements
# ---------------------------------------------------------------------------

def test_uc_019_broadcast_health_announcements():
    """test_id: UC-TEST-019 | source_id: PHC-UC-12 Main Flow.

    Verify PHC Staff broadcasts health announcements to patients.
    """
    ann = publish_health_announcement(
        title="Annual Flu Vaccination Camp",
        content="Free vaccination at PHC premises this Saturday.",
        priority="Normal",
        published_by_user_id=10,
    )
    assert ann.id is not None
    assert ann.is_active is True
    active = list_active_announcements()
    assert ann in active


# ---------------------------------------------------------------------------
# PHC-UC-13: Generate System Reports
# ---------------------------------------------------------------------------

def test_uc_020_generate_system_reports(stub_iam, user_ref):
    """test_id: UC-TEST-020 | source_id: PHC-UC-13 Main Flow.

    Verify PHC Staff generates anonymized administrative reports.
    """
    stub_iam(users={2001: user_ref(2001)})
    rep = generate_administrative_report("demographics")
    assert rep["anonymized"] is True
    assert "total_unique_patients" in rep


def test_uc_021_generate_system_reports_invalid_parameter():
    """test_id: UC-TEST-021 | source_id: PHC-UC-13 Exception E1.

    Verify report generation with invalid report type parameter is rejected.
    """
    with pytest.raises(ValueError):
        generate_administrative_report("invalid_unknown_type")


# ---------------------------------------------------------------------------
# PHC-UC-14: Mark Requisition as Fulfilled
# ---------------------------------------------------------------------------

def test_uc_022_mark_requisition_as_fulfilled():
    """test_id: UC-TEST-022 | source_id: PHC-UC-14 Main Flow.

    Verify PHC Staff marks approved requisition as Fulfilled after delivery.
    """
    item = create_or_update_item(item_code="MED-UC-FUL-01", name="Bandages Pack")
    req = submit_procurement_requisition(
        originator_user_id=10,
        originator_username="staff_user",
        justification="Restock",
        items_data=[{"item_id": item.id, "quantity": 50}],
    )
    decide_procurement_requisition(req.id, approve=True, actor_user_id=30, actor_username="director")

    fulfilled = fulfill_procurement_requisition(req.id, actor_user_id=10, actor_username="staff_user")
    assert fulfilled.status == RequisitionStatus.FULFILLED.value


def test_uc_023_fulfill_non_approved_requisition_blocked():
    """test_id: UC-TEST-023 | source_id: PHC-UC-14 Exception E1.

    Verify marking requisition Fulfilled is blocked when requisition is not Approved.
    """
    item = create_or_update_item(item_code="MED-UC-FUL-02", name="Gauze")
    req = submit_procurement_requisition(
        originator_user_id=10,
        originator_username="staff_user",
        justification="Restock",
        items_data=[{"item_id": item.id, "quantity": 10}],
    )
    # Requisition is still PENDING_APPROVAL
    with pytest.raises(RequisitionNotApprovedError):
        fulfill_procurement_requisition(req.id, actor_user_id=10, actor_username="staff_user")


# ---------------------------------------------------------------------------
# PHC-UC-15: Review Reimbursement Claim
# ---------------------------------------------------------------------------

def test_uc_024_review_reimbursement_claim():
    """test_id: UC-TEST-024 | source_id: PHC-UC-15 Main Flow.

    Verify PHC Staff reviews submitted claim and forwards to Accounts.
    """
    visit = create_patient_visit(patient_user_id=1001, symptoms="Check", diagnosis="OK", created_by_user_id=10, created_by_username="staff")
    presc = create_prescription(visit_id=visit.id, prescription_number="RX-UC-15-01", medicines_prescribed="Meds", created_by_user_id=10, created_by_username="staff")
    claim = submit_reimbursement_claim(claimant_user_id=1001, claimant_kind="faculty", claimant_username="prof1001", prescription_id=presc.id, expense_date=timezone.now().date(), amount_claimed=Decimal("1200.00"))

    reviewed = review_claim_phc(claim.id, actor_user_id=10, actor_username="staff_user", comments="Documents OK")
    assert reviewed.status == ReimbursementStatus.PENDING_ACCOUNTS_VERIFICATION.value


# ---------------------------------------------------------------------------
# PHC-UC-16: Decide Inventory Requisition
# ---------------------------------------------------------------------------

def test_uc_025_decide_requisition_alt1_approve():
    """test_id: UC-TEST-025 | source_id: PHC-UC-16 Alternative A1.

    Verify Approving Authority approves pending inventory requisition.
    """
    item = create_or_update_item(item_code="MED-UC-DEC-01", name="IV Fluids")
    req = submit_procurement_requisition(originator_user_id=10, originator_username="staff", justification="Low stock", items_data=[{"item_id": item.id, "quantity": 40}])

    approved = decide_procurement_requisition(req.id, approve=True, actor_user_id=30, actor_username="director")
    assert approved.status == RequisitionStatus.APPROVED.value


def test_uc_026_decide_requisition_alt2_reject():
    """test_id: UC-TEST-026 | source_id: PHC-UC-16 Alternative A2.

    Verify Approving Authority rejects pending inventory requisition.
    """
    item = create_or_update_item(item_code="MED-UC-DEC-02", name="Expensive Kit")
    req = submit_procurement_requisition(originator_user_id=10, originator_username="staff", justification="Need kit", items_data=[{"item_id": item.id, "quantity": 5}])

    rejected = decide_procurement_requisition(req.id, approve=False, actor_user_id=30, actor_username="director", remarks="Not permitted")
    assert rejected.status == RequisitionStatus.REJECTED.value


def test_uc_027_decide_requisition_exc1_duplicate_decision():
    """test_id: UC-TEST-027 | source_id: PHC-UC-16 Exception E1.

    Verify duplicate decision blocked when requisition is no longer Pending Approval.
    """
    item = create_or_update_item(item_code="MED-UC-DEC-03", name="Reagent")
    req = submit_procurement_requisition(originator_user_id=10, originator_username="staff", justification="Need reagent", items_data=[{"item_id": item.id, "quantity": 10}])
    decide_procurement_requisition(req.id, approve=True, actor_user_id=30, actor_username="director")

    with pytest.raises(InvalidStateTransitionError):
        decide_procurement_requisition(req.id, approve=False, actor_user_id=30, actor_username="director")


# ---------------------------------------------------------------------------
# PHC-UC-19: Verify Reimbursement Claim
# ---------------------------------------------------------------------------

def test_uc_028_verify_reimbursement_claim():
    """test_id: UC-TEST-028 | source_id: PHC-UC-19 Main Flow.

    Verify Accounts & Audit verifies financial details of reimbursement claim.
    """
    visit = create_patient_visit(patient_user_id=1001, symptoms="Check", diagnosis="OK", created_by_user_id=10, created_by_username="staff")
    presc = create_prescription(visit_id=visit.id, prescription_number="RX-UC-19-01", medicines_prescribed="Meds", created_by_user_id=10, created_by_username="staff")
    claim = submit_reimbursement_claim(claimant_user_id=1001, claimant_kind="faculty", claimant_username="prof1001", prescription_id=presc.id, expense_date=timezone.now().date(), amount_claimed=Decimal("1500.00"))
    review_claim_phc(claim.id, actor_user_id=10, actor_username="staff")

    verified = verify_claim_accounts(claim.id, actor_user_id=20, actor_username="auditor", amount_verified=Decimal("1400.00"))
    assert verified.status == ReimbursementStatus.PENDING_SANCTION.value
    assert verified.amount_approved == Decimal("1400.00")


# ---------------------------------------------------------------------------
# PHC-UC-20: Decide Reimbursement Sanction
# ---------------------------------------------------------------------------

def test_uc_029_decide_sanction_alt1_approve():
    """test_id: UC-TEST-029 | source_id: PHC-UC-20 Alternative A1.

    Verify Approving Authority approves reimbursement sanction.
    """
    visit = create_patient_visit(patient_user_id=1001, symptoms="Check", diagnosis="OK", created_by_user_id=10, created_by_username="staff")
    presc = create_prescription(visit_id=visit.id, prescription_number="RX-UC-20-01", medicines_prescribed="Meds", created_by_user_id=10, created_by_username="staff")
    claim = submit_reimbursement_claim(claimant_user_id=1001, claimant_kind="faculty", claimant_username="prof1001", prescription_id=presc.id, expense_date=timezone.now().date(), amount_claimed=Decimal("500.00"))
    review_claim_phc(claim.id, actor_user_id=10, actor_username="staff")
    verify_claim_accounts(claim.id, actor_user_id=20, actor_username="auditor")

    sanctioned = decide_claim_sanction(claim.id, approve=True, actor_user_id=30, actor_username="director")
    assert sanctioned.status == ReimbursementStatus.APPROVED_FOR_PAYMENT.value


def test_uc_030_decide_sanction_alt2_reject():
    """test_id: UC-TEST-030 | source_id: PHC-UC-20 Alternative A2.

    Verify Approving Authority rejects reimbursement sanction terminating the claim.
    """
    visit = create_patient_visit(patient_user_id=1001, symptoms="Check", diagnosis="OK", created_by_user_id=10, created_by_username="staff")
    presc = create_prescription(visit_id=visit.id, prescription_number="RX-UC-20-02", medicines_prescribed="Meds", created_by_user_id=10, created_by_username="staff")
    claim = submit_reimbursement_claim(claimant_user_id=1001, claimant_kind="faculty", claimant_username="prof1001", prescription_id=presc.id, expense_date=timezone.now().date(), amount_claimed=Decimal("500.00"))
    review_claim_phc(claim.id, actor_user_id=10, actor_username="staff")
    verify_claim_accounts(claim.id, actor_user_id=20, actor_username="auditor")

    rejected = decide_claim_sanction(claim.id, approve=False, actor_user_id=30, actor_username="director", comments="Budget limit")
    assert rejected.status == ReimbursementStatus.REJECTED.value


def test_uc_031_decide_sanction_exc1_duplicate_decision():
    """test_id: UC-TEST-031 | source_id: PHC-UC-20 Exception E1.

    Verify duplicate sanction decision blocked when claim is no longer Pending Sanction.
    """
    visit = create_patient_visit(patient_user_id=1001, symptoms="Check", diagnosis="OK", created_by_user_id=10, created_by_username="staff")
    presc = create_prescription(visit_id=visit.id, prescription_number="RX-UC-20-03", medicines_prescribed="Meds", created_by_user_id=10, created_by_username="staff")
    claim = submit_reimbursement_claim(claimant_user_id=1001, claimant_kind="faculty", claimant_username="prof1001", prescription_id=presc.id, expense_date=timezone.now().date(), amount_claimed=Decimal("500.00"))
    review_claim_phc(claim.id, actor_user_id=10, actor_username="staff")
    verify_claim_accounts(claim.id, actor_user_id=20, actor_username="auditor")
    decide_claim_sanction(claim.id, approve=True, actor_user_id=30, actor_username="director")

    with pytest.raises(InvalidStateTransitionError):
        decide_claim_sanction(claim.id, approve=False, actor_user_id=30, actor_username="director")


# ---------------------------------------------------------------------------
# PHC-UC-21: Process Reimbursement Payment
# ---------------------------------------------------------------------------

def test_uc_032_process_reimbursement_payment():
    """test_id: UC-TEST-032 | source_id: PHC-UC-21 Main Flow.

    Verify Accounts & Audit processes reimbursement payment closing claim.
    """
    visit = create_patient_visit(patient_user_id=1001, symptoms="Check", diagnosis="OK", created_by_user_id=10, created_by_username="staff")
    presc = create_prescription(visit_id=visit.id, prescription_number="RX-UC-21-01", medicines_prescribed="Meds", created_by_user_id=10, created_by_username="staff")
    claim = submit_reimbursement_claim(claimant_user_id=1001, claimant_kind="faculty", claimant_username="prof1001", prescription_id=presc.id, expense_date=timezone.now().date(), amount_claimed=Decimal("1500.00"))
    review_claim_phc(claim.id, actor_user_id=10, actor_username="staff")
    verify_claim_accounts(claim.id, actor_user_id=20, actor_username="auditor")
    decide_claim_sanction(claim.id, approve=True, actor_user_id=30, actor_username="director")

    paid = process_claim_payment(claim.id, actor_user_id=20, actor_username="accounts", payment_reference="PAY-REF-554433")
    assert paid.status == ReimbursementStatus.REIMBURSED.value


# ---------------------------------------------------------------------------
# PHC-UC-22: Create & Publish Doctor Schedule
# ---------------------------------------------------------------------------

def test_uc_033_create_and_publish_doctor_schedule():
    """test_id: UC-TEST-033 | source_id: PHC-UC-22 Main Flow.

    Verify PHC Staff creates and publishes doctor schedule.
    """
    doc = create_doctor(name="Dr. S. Mukherjee", specialization="Neurology")
    sched = create_or_update_schedule(
        doctor_id=doc.id,
        day_of_week="Thursday",
        start_time=time(11, 0),
        end_time=time(14, 0),
        room_number="Room 401",
        is_published=True,
    )
    assert sched.id is not None
    assert sched.is_published is True
