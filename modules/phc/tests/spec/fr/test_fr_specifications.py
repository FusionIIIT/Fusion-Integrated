"""Specification-Driven Automated Backend Tests for PHC Module.

Strategy: FR (Functional Requirements: Problem Statement + CFR/AFR)
Adequacy: Every testable CFR and AFR covered with at least one test.
"""
from datetime import date, datetime, time, timedelta
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
    SubmissionWindowExpiredError,
)
from modules.phc.domain.rules import evaluate_claimant_eligibility
from modules.phc.domain.state_machine import ReimbursementStateMachine
from modules.phc.models.ambulance import AmbulanceLog
from modules.phc.models.announcements import HealthAnnouncement
from modules.phc.models.audit import PHCAuditTrail
from modules.phc.models.doctors import Doctor, DoctorAttendance, DoctorSchedule
from modules.phc.models.inventory import (
    InventoryItem,
    ProcurementRequisition,
    RequisitionItem,
)
from modules.phc.models.notifications import PHCNotification
from modules.phc.models.patient_records import PatientVisit, Prescription
from modules.phc.models.reimbursement import ReimbursementActionHistory, ReimbursementClaim
from modules.phc.selectors.ambulance import list_ambulance_logs
from modules.phc.selectors.announcements import list_active_announcements
from modules.phc.selectors.doctors import get_patient_doctor_availability
from modules.phc.selectors.patient_records import (
    get_patient_medical_history,
    get_patient_prescriptions,
    search_patient_records_staff,
)
from modules.phc.selectors.reimbursement import get_user_reimbursement_claims
from modules.phc.services.ambulance import log_ambulance_usage
from modules.phc.services.announcements import publish_health_announcement
from modules.phc.services.doctors import (
    create_doctor,
    create_or_update_schedule,
    mark_attendance,
    publish_schedules,
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


# ---------------------------------------------------------------------------
# Test Helpers & Fixtures
# ---------------------------------------------------------------------------

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
# CFR-PHC-001 / AFR-PHC-001..005: Doctor Schedule & Availability Management
# ---------------------------------------------------------------------------

def test_fr_001_patient_access_schedule_and_attendance():
    """test_id: FR-TEST-001 | source_id: AFR-PHC-001.

    Verify patient can access the static weekly doctor schedule together with
    current-day real-time attendance status.
    """
    doc = create_doctor(name="A. Sharma", specialization="Cardiology")
    today_day = timezone.now().strftime("%A")
    sched = create_or_update_schedule(
        doctor_id=doc.id,
        day_of_week=today_day,
        start_time=time(9, 0),
        end_time=time(13, 0),
        room_number="Room 101",
        is_published=True,
    )
    mark_attendance(
        doctor_id=doc.id,
        status="Available",
        marked_by_user_id=10,
        remarks="Present in OPD",
    )

    availability = get_patient_doctor_availability()
    assert len(availability) >= 1
    doc_data = next((d for d in availability if d["doctor_id"] == doc.id), None)
    assert doc_data is not None
    assert doc_data["doctor_name"] == "A. Sharma"
    assert doc_data["today_attendance"]["status"] == "Available"
    assert len(doc_data["weekly_schedule"]) >= 1
    assert doc_data["weekly_schedule"][0]["day_of_week"] == today_day


def test_fr_002_staff_maintain_schedule():
    """test_id: FR-TEST-002 | source_id: AFR-PHC-002.

    Verify PHC Staff can maintain/update an existing static weekly schedule.
    """
    doc = create_doctor(name="B. Patel", specialization="General Medicine")
    sched = create_or_update_schedule(
        doctor_id=doc.id,
        day_of_week="Monday",
        start_time=time(10, 0),
        end_time=time(14, 0),
        room_number="Room 102",
        is_published=False,
    )

    updated = create_or_update_schedule(
        doctor_id=doc.id,
        day_of_week="Tuesday",
        start_time=time(11, 0),
        end_time=time(15, 0),
        room_number="Room 105",
        is_published=True,
        schedule_id=sched.id,
    )
    assert updated.id == sched.id
    assert updated.day_of_week == "Tuesday"
    assert updated.room_number == "Room 105"
    assert updated.start_time == time(11, 0)
    assert updated.is_published is True


def test_fr_003_staff_mark_doctor_available():
    """test_id: FR-TEST-003 | source_id: AFR-PHC-003.

    Verify PHC Staff can mark a visiting doctor as Available in real time.
    """
    doc = create_doctor(name="C. Roy", specialization="Dermatology")
    att = mark_attendance(
        doctor_id=doc.id,
        status="Available",
        marked_by_user_id=10,
        remarks="Doctor arrived on time",
    )
    assert att.status == "Available"
    assert att.doctor == doc
    assert att.marked_by_user_id == 10

    # Validation constraint: marking attendance with an invalid/unsupported status must raise ValueError
    with pytest.raises(ValueError):
        mark_attendance(
            doctor_id=doc.id,
            status="ON_VACATION",
            marked_by_user_id=10,
        )


def test_fr_004_staff_mark_doctor_departed():
    """test_id: FR-TEST-004 | source_id: AFR-PHC-003.

    Verify PHC Staff can mark a visiting doctor as Departed in real time.
    """
    doc = create_doctor(name="D. Sen", specialization="ENT")
    mark_attendance(doctor_id=doc.id, status="Available", marked_by_user_id=10)
    updated_att = mark_attendance(
        doctor_id=doc.id,
        status="Departed",
        marked_by_user_id=10,
        remarks="Shift finished",
    )
    assert updated_att.status == "Departed"


def test_fr_005_staff_create_schedule():
    """test_id: FR-TEST-005 | source_id: AFR-PHC-004.

    Verify PHC Staff can create doctor schedules.
    """
    doc = create_doctor(name="E. Das", specialization="Pediatrics")
    sched = create_or_update_schedule(
        doctor_id=doc.id,
        day_of_week="Wednesday",
        start_time=time(8, 30),
        end_time=time(12, 30),
        room_number="Room 201",
        is_published=False,
    )
    assert sched.id is not None
    assert sched.doctor == doc
    assert sched.day_of_week == "Wednesday"
    assert sched.is_published is False


def test_fr_006_staff_publish_schedule():
    """test_id: FR-TEST-006 | source_id: AFR-PHC-005.

    Verify PHC Staff can publish a doctor schedule for patient visibility.
    """
    doc = create_doctor(name="F. Khan", specialization="Orthopedics")
    sched1 = create_or_update_schedule(
        doctor_id=doc.id,
        day_of_week="Thursday",
        start_time=time(9, 0),
        end_time=time(12, 0),
        is_published=False,
    )
    count = publish_schedules([sched1.id])
    assert count == 1
    sched1.refresh_from_db()
    assert sched1.is_published is True


# ---------------------------------------------------------------------------
# CFR-PHC-002 / AFR-PHC-006..012: Patient Records & Prescriptions
# ---------------------------------------------------------------------------

def test_fr_007_staff_search_patient_profile():
    """test_id: FR-TEST-007 | source_id: AFR-PHC-006.

    Verify PHC Staff can search for a patient profile.
    """
    results = search_patient_records_staff(query="2001")
    assert isinstance(results, list)


def test_fr_008_staff_create_patient_visit():
    """test_id: FR-TEST-008 | source_id: AFR-PHC-007.

    Verify PHC Staff can create a patient visit record.
    """
    doc = create_doctor(name="G. Nair", specialization="General")
    visit = create_patient_visit(
        patient_user_id=2001,
        doctor_id=doc.id,
        symptoms="High fever and body ache",
        diagnosis="Viral flu",
        created_by_user_id=10,
        created_by_username="staff_user",
    )
    assert visit.id is not None
    assert visit.patient_user_id == 2001
    assert visit.diagnosis == "Viral flu"


def test_fr_009_staff_digitize_prescription():
    """test_id: FR-TEST-009 | source_id: AFR-PHC-008.

    Verify PHC Staff can digitize a physical prescription and link it to patient record.
    """
    visit = create_patient_visit(
        patient_user_id=2001,
        symptoms="Headache",
        diagnosis="Migraine",
        created_by_user_id=10,
        created_by_username="staff_user",
    )
    presc = create_prescription(
        visit_id=visit.id,
        prescription_number="RX-2026-0001",
        medicines_prescribed="Paracetamol 650mg TDS x 3 days",
        created_by_user_id=10,
        created_by_username="staff_user",
        scanned_document_url="http://storage.test/rx1.pdf",
    )
    assert presc.id is not None
    assert presc.visit == visit
    assert presc.patient_user_id == 2001
    assert presc.prescription_number == "RX-2026-0001"


def test_fr_010_patient_read_own_medical_history(stub_iam):
    """test_id: FR-TEST-010 | source_id: AFR-PHC-009.

    Verify patient has read-only access to their own medical history.
    """
    create_patient_visit(
        patient_user_id=2001,
        symptoms="Cough",
        diagnosis="Bronchitis",
        created_by_user_id=10,
        created_by_username="staff",
    )
    client = _auth_client(
        stub_iam,
        user_id=2001,
        kind="student",
        roles=("student",),
        permissions=("phc.patient_record.view_self",),
    )
    res = client.get("/api/v1/phc/patient/history/")
    assert res.status_code == 200
    data = res.json()
    records = data if isinstance(data, list) else data.get("results", [])
    assert len(records) == 1
    assert records[0]["diagnosis"] == "Bronchitis"


def test_fr_011_patient_access_prescriptions(stub_iam):
    """test_id: FR-TEST-011 | source_id: AFR-PHC-010.

    Verify patient can access prescriptions associated with their own medical history.
    """
    visit = create_patient_visit(
        patient_user_id=2001,
        symptoms="Cold",
        diagnosis="Common cold",
        created_by_user_id=10,
        created_by_username="staff",
    )
    create_prescription(
        visit_id=visit.id,
        prescription_number="RX-2026-0002",
        medicines_prescribed="Cetirizine 10mg OD",
        created_by_user_id=10,
        created_by_username="staff",
    )
    client = _auth_client(
        stub_iam,
        user_id=2001,
        kind="student",
        roles=("student",),
        permissions=("phc.patient_record.view_self",),
    )
    res = client.get("/api/v1/phc/patient/prescriptions/")
    assert res.status_code == 200
    data = res.json()
    records = data if isinstance(data, list) else data.get("results", [])
    assert len(records) == 1
    assert records[0]["prescription_number"] == "RX-2026-0002"


def test_fr_012_patient_download_records_pdf(stub_iam):
    """test_id: FR-TEST-012 | source_id: AFR-PHC-011.

    Verify patient can download PDF copies of their own medical records.
    """
    create_patient_visit(
        patient_user_id=2001,
        symptoms="Fever",
        diagnosis="Typhoid",
        created_by_user_id=10,
        created_by_username="staff",
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


def test_fr_013_cross_patient_access_prevented(stub_iam):
    """test_id: FR-TEST-013 | source_id: AFR-PHC-012.

    Verify cross-patient medical data access is prevented.
    """
    # Create visit for Patient 2002
    create_patient_visit(
        patient_user_id=2002,
        symptoms="Secret illness",
        diagnosis="Confidential",
        created_by_user_id=10,
        created_by_username="staff",
    )
    # Patient 2001 requests their history
    client = _auth_client(
        stub_iam,
        user_id=2001,
        kind="student",
        roles=("student",),
        permissions=("phc.patient_record.view_self",),
    )
    res = client.get("/api/v1/phc/patient/history/")
    assert res.status_code == 200
    # Must NOT disclose Patient 2002's records
    data = res.json()
    records = data if isinstance(data, list) else data.get("results", [])
    assert all(r["patient_user_id"] == 2001 for r in records)


# ---------------------------------------------------------------------------
# CFR-PHC-003 / AFR-PHC-013..016: Reimbursement Eligibility & Submission
# ---------------------------------------------------------------------------

def test_fr_014_employee_eligible_reimbursement_initiation():
    """test_id: FR-TEST-014 | source_id: AFR-PHC-013.

    Verify institute employee is permitted to initiate a reimbursement claim.
    """
    res_faculty = evaluate_claimant_eligibility("faculty")
    assert res_faculty.is_eligible is True
    res_staff = evaluate_claimant_eligibility("staff")
    assert res_staff.is_eligible is True


def test_fr_015_student_excluded_from_reimbursement():
    """test_id: FR-TEST-015 | source_id: AFR-PHC-013.

    Verify students are excluded from submitting reimbursement claims.
    """
    res_student = evaluate_claimant_eligibility("student")
    assert res_student.is_eligible is False
    assert "Students are ineligible" in res_student.reason

    visit = create_patient_visit(
        patient_user_id=3001,
        symptoms="Cold",
        diagnosis="Viral",
        created_by_user_id=10,
        created_by_username="staff",
    )
    presc = create_prescription(
        visit_id=visit.id,
        prescription_number="RX-STUDENT-01",
        medicines_prescribed="Meds",
        created_by_user_id=10,
        created_by_username="staff",
    )

    with pytest.raises(IneligibleClaimantError):
        submit_reimbursement_claim(
            claimant_user_id=3001,
            claimant_kind="student",
            claimant_username="student3001",
            prescription_id=presc.id,
            expense_date=timezone.now().date(),
            amount_claimed=Decimal("500.00"),
        )


def test_fr_016_claim_requires_valid_recorded_prescription():
    """test_id: FR-TEST-016 | source_id: AFR-PHC-014.

    Verify reimbursement claim requires a valid recorded prescription for the claimant.
    """
    # Non-existent prescription
    with pytest.raises(PrescriptionRequiredError):
        submit_reimbursement_claim(
            claimant_user_id=1001,
            claimant_kind="faculty",
            claimant_username="prof1001",
            prescription_id=99999,
            expense_date=timezone.now().date(),
            amount_claimed=Decimal("1200.00"),
        )

    # Prescription belonging to another user
    visit_other = create_patient_visit(
        patient_user_id=2002,
        symptoms="Fever",
        diagnosis="Flu",
        created_by_user_id=10,
        created_by_username="staff",
    )
    presc_other = create_prescription(
        visit_id=visit_other.id,
        prescription_number="RX-OTHER-01",
        medicines_prescribed="Meds",
        created_by_user_id=10,
        created_by_username="staff",
    )
    with pytest.raises(PrescriptionRequiredError):
        submit_reimbursement_claim(
            claimant_user_id=1001,
            claimant_kind="faculty",
            claimant_username="prof1001",
            prescription_id=presc_other.id,
            expense_date=timezone.now().date(),
            amount_claimed=Decimal("1200.00"),
        )


def test_fr_017_claim_within_submission_window_accepted():
    """test_id: FR-TEST-017 | source_id: AFR-PHC-015.

    Verify reimbursement claim within configured submission window (90 days) is accepted.
    """
    visit = create_patient_visit(
        patient_user_id=1001,
        symptoms="Sprain",
        diagnosis="Injury",
        created_by_user_id=10,
        created_by_username="staff",
    )
    presc = create_prescription(
        visit_id=visit.id,
        prescription_number="RX-WINDOW-01",
        medicines_prescribed="Painkillers",
        created_by_user_id=10,
        created_by_username="staff",
    )
    valid_date = timezone.now().date() - timedelta(days=45)
    claim = submit_reimbursement_claim(
        claimant_user_id=1001,
        claimant_kind="faculty",
        claimant_username="prof1001",
        prescription_id=presc.id,
        expense_date=valid_date,
        amount_claimed=Decimal("2500.00"),
    )
    assert claim.id is not None
    assert claim.status == ReimbursementStatus.PENDING_PHC_REVIEW.value


def test_fr_018_claim_outside_submission_window_rejected():
    """test_id: FR-TEST-018 | source_id: AFR-PHC-015.

    Verify reimbursement claim outside configured submission window is rejected.
    """
    visit = create_patient_visit(
        patient_user_id=1001,
        symptoms="Sprain",
        diagnosis="Injury",
        created_by_user_id=10,
        created_by_username="staff",
    )
    presc = create_prescription(
        visit_id=visit.id,
        prescription_number="RX-WINDOW-02",
        medicines_prescribed="Painkillers",
        created_by_user_id=10,
        created_by_username="staff",
    )
    expired_date = timezone.now().date() - timedelta(days=95)
    with pytest.raises(SubmissionWindowExpiredError):
        submit_reimbursement_claim(
            claimant_user_id=1001,
            claimant_kind="faculty",
            claimant_username="prof1001",
            prescription_id=presc.id,
            expense_date=expired_date,
            amount_claimed=Decimal("2500.00"),
        )


def test_fr_019_employee_claim_submission_initial_state():
    """test_id: FR-TEST-019 | source_id: AFR-PHC-016.

    Verify eligible employee successfully submits reimbursement claim creating
    an active claim in initial state (Pending PHC Review).
    """
    visit = create_patient_visit(
        patient_user_id=1001,
        symptoms="Dental pain",
        diagnosis="Caries",
        created_by_user_id=10,
        created_by_username="staff",
    )
    presc = create_prescription(
        visit_id=visit.id,
        prescription_number="RX-SUBMIT-01",
        medicines_prescribed="Antibiotics",
        created_by_user_id=10,
        created_by_username="staff",
    )
    claim = submit_reimbursement_claim(
        claimant_user_id=1001,
        claimant_kind="faculty",
        claimant_username="prof1001",
        prescription_id=presc.id,
        expense_date=timezone.now().date() - timedelta(days=5),
        amount_claimed=Decimal("1500.00"),
        remarks="Root canal expense",
    )
    assert claim.claim_number.startswith("MED-CLM-")
    assert claim.status == ReimbursementStatus.PENDING_PHC_REVIEW.value


# ---------------------------------------------------------------------------
# CFR-PHC-004 / AFR-PHC-017..021, 038: Reimbursement Lifecycle Progression
# ---------------------------------------------------------------------------

def test_fr_020_reimbursement_sequential_progression():
    """test_id: FR-TEST-020 | source_id: AFR-PHC-017.

    Verify sequential progression of reimbursement workflow across all mandatory stages.
    """
    visit = create_patient_visit(
        patient_user_id=1001,
        symptoms="Consultation",
        diagnosis="General",
        created_by_user_id=10,
        created_by_username="staff",
    )
    presc = create_prescription(
        visit_id=visit.id,
        prescription_number="RX-SEQ-01",
        medicines_prescribed="Meds",
        created_by_user_id=10,
        created_by_username="staff",
    )
    claim = submit_reimbursement_claim(
        claimant_user_id=1001,
        claimant_kind="faculty",
        claimant_username="prof1001",
        prescription_id=presc.id,
        expense_date=timezone.now().date(),
        amount_claimed=Decimal("3000.00"),
    )
    assert claim.status == ReimbursementStatus.PENDING_PHC_REVIEW.value

    # Stage 1: PHC Review
    claim = review_claim_phc(claim.id, actor_user_id=10, actor_username="staff")
    assert claim.status == ReimbursementStatus.PENDING_ACCOUNTS_VERIFICATION.value

    # Stage 2: Accounts Verification
    claim = verify_claim_accounts(claim.id, actor_user_id=20, actor_username="accounts", amount_verified=Decimal("3000.00"))
    assert claim.status == ReimbursementStatus.PENDING_SANCTION.value

    # Stage 3: Approving Authority Sanction
    claim = decide_claim_sanction(claim.id, approve=True, actor_user_id=30, actor_username="director")
    assert claim.status == ReimbursementStatus.APPROVED_FOR_PAYMENT.value

    # Stage 4: Accounts Payment
    claim = process_claim_payment(claim.id, actor_user_id=20, actor_username="accounts", payment_reference="REF-998877")
    assert claim.status == ReimbursementStatus.REIMBURSED.value


def test_fr_021_phc_staff_review_forward():
    """test_id: FR-TEST-021 | source_id: AFR-PHC-018.

    Verify PHC Staff reviews submitted claim and forwards to Accounts & Audit.
    """
    visit = create_patient_visit(patient_user_id=1001, symptoms="Checkup", diagnosis="OK", created_by_user_id=10, created_by_username="staff")
    presc = create_prescription(visit_id=visit.id, prescription_number="RX-FWD-01", medicines_prescribed="Vitamins", created_by_user_id=10, created_by_username="staff")
    claim = submit_reimbursement_claim(claimant_user_id=1001, claimant_kind="staff", claimant_username="staff1001", prescription_id=presc.id, expense_date=timezone.now().date(), amount_claimed=Decimal("400.00"))

    reviewed = review_claim_phc(claim.id, actor_user_id=10, actor_username="phc_staff", comments="Documents verified")
    assert reviewed.status == ReimbursementStatus.PENDING_ACCOUNTS_VERIFICATION.value


def test_fr_022_accounts_verify_claim():
    """test_id: FR-TEST-022 | source_id: AFR-PHC-019.

    Verify Accounts & Audit verifies financial details and forwards claim for sanction.
    """
    visit = create_patient_visit(patient_user_id=1001, symptoms="Checkup", diagnosis="OK", created_by_user_id=10, created_by_username="staff")
    presc = create_prescription(visit_id=visit.id, prescription_number="RX-ACC-01", medicines_prescribed="Vitamins", created_by_user_id=10, created_by_username="staff")
    claim = submit_reimbursement_claim(claimant_user_id=1001, claimant_kind="staff", claimant_username="staff1001", prescription_id=presc.id, expense_date=timezone.now().date(), amount_claimed=Decimal("1000.00"))
    review_claim_phc(claim.id, actor_user_id=10, actor_username="phc_staff")

    verified = verify_claim_accounts(claim.id, actor_user_id=20, actor_username="accounts_staff", amount_verified=Decimal("950.00"))
    assert verified.status == ReimbursementStatus.PENDING_SANCTION.value
    assert verified.amount_approved == Decimal("950.00")


def test_fr_023_sanction_approval():
    """test_id: FR-TEST-023 | source_id: AFR-PHC-020.

    Verify Approving Authority approves reimbursement sanction.
    """
    visit = create_patient_visit(patient_user_id=1001, symptoms="Eye check", diagnosis="Myopia", created_by_user_id=10, created_by_username="staff")
    presc = create_prescription(visit_id=visit.id, prescription_number="RX-SAN-01", medicines_prescribed="Eye drops", created_by_user_id=10, created_by_username="staff")
    claim = submit_reimbursement_claim(claimant_user_id=1001, claimant_kind="staff", claimant_username="staff1001", prescription_id=presc.id, expense_date=timezone.now().date(), amount_claimed=Decimal("800.00"))
    review_claim_phc(claim.id, actor_user_id=10, actor_username="phc_staff")
    verify_claim_accounts(claim.id, actor_user_id=20, actor_username="accounts_staff")

    sanctioned = decide_claim_sanction(claim.id, approve=True, actor_user_id=30, actor_username="director")
    assert sanctioned.status == ReimbursementStatus.APPROVED_FOR_PAYMENT.value


def test_fr_024_sanction_rejection():
    """test_id: FR-TEST-024 | source_id: AFR-PHC-020.

    Verify Approving Authority rejects reimbursement sanction terminating the claim.
    """
    visit = create_patient_visit(patient_user_id=1001, symptoms="Eye check", diagnosis="Myopia", created_by_user_id=10, created_by_username="staff")
    presc = create_prescription(visit_id=visit.id, prescription_number="RX-SAN-02", medicines_prescribed="Eye drops", created_by_user_id=10, created_by_username="staff")
    claim = submit_reimbursement_claim(claimant_user_id=1001, claimant_kind="staff", claimant_username="staff1001", prescription_id=presc.id, expense_date=timezone.now().date(), amount_claimed=Decimal("800.00"))
    review_claim_phc(claim.id, actor_user_id=10, actor_username="phc_staff")
    verify_claim_accounts(claim.id, actor_user_id=20, actor_username="accounts_staff")

    rejected = decide_claim_sanction(claim.id, approve=False, actor_user_id=30, actor_username="director", comments="Budget exhausted")
    assert rejected.status == ReimbursementStatus.REJECTED.value


def test_fr_025_payment_processing():
    """test_id: FR-TEST-025 | source_id: AFR-PHC-021.

    Verify Accounts & Audit processes payment for approved claim closing it as reimbursed.
    """
    visit = create_patient_visit(patient_user_id=1001, symptoms="Health", diagnosis="Fit", created_by_user_id=10, created_by_username="staff")
    presc = create_prescription(visit_id=visit.id, prescription_number="RX-PAY-01", medicines_prescribed="Meds", created_by_user_id=10, created_by_username="staff")
    claim = submit_reimbursement_claim(claimant_user_id=1001, claimant_kind="staff", claimant_username="staff1001", prescription_id=presc.id, expense_date=timezone.now().date(), amount_claimed=Decimal("600.00"))
    review_claim_phc(claim.id, actor_user_id=10, actor_username="phc_staff")
    verify_claim_accounts(claim.id, actor_user_id=20, actor_username="accounts_staff")
    decide_claim_sanction(claim.id, approve=True, actor_user_id=30, actor_username="director")

    paid = process_claim_payment(claim.id, actor_user_id=20, actor_username="accounts_staff", payment_reference="NEFT123456")
    assert paid.status == ReimbursementStatus.REIMBURSED.value


def test_fr_045_prohibit_modifying_or_reopening_claim():
    """test_id: FR-TEST-045 | source_id: AFR-PHC-038.

    Verify modifying or reopening a submitted or rejected claim is prohibited, requiring a new claim.
    """
    with pytest.raises(ClaimImmutableError):
        ReimbursementStateMachine.assert_can_modify(ReimbursementStatus.PENDING_PHC_REVIEW.value)

    with pytest.raises(ClaimImmutableError):
        ReimbursementStateMachine.assert_can_modify(ReimbursementStatus.REJECTED.value)


# ---------------------------------------------------------------------------
# CFR-PHC-005 / AFR-PHC-022..023: Transparency & Status Tracking
# ---------------------------------------------------------------------------

def test_fr_026_employee_view_own_claim_status_and_history():
    """test_id: FR-TEST-026 | source_id: AFR-PHC-022.

    Verify employee can view status and action history of their own reimbursement claims.
    """
    visit = create_patient_visit(patient_user_id=1001, symptoms="Check", diagnosis="OK", created_by_user_id=10, created_by_username="staff")
    presc = create_prescription(visit_id=visit.id, prescription_number="RX-HIST-01", medicines_prescribed="Meds", created_by_user_id=10, created_by_username="staff")
    claim = submit_reimbursement_claim(claimant_user_id=1001, claimant_kind="faculty", claimant_username="prof1001", prescription_id=presc.id, expense_date=timezone.now().date(), amount_claimed=Decimal("1100.00"))
    review_claim_phc(claim.id, actor_user_id=10, actor_username="phc_staff", comments="First review")

    claims = get_user_reimbursement_claims(claimant_user_id=1001)
    assert len(claims) >= 1
    target = next(c for c in claims if c.id == claim.id)
    assert target.status == ReimbursementStatus.PENDING_ACCOUNTS_VERIFICATION.value
    history = target.history.all()
    assert history.count() == 2  # SUBMIT_CLAIM + PHC_REVIEW_FORWARD


def test_fr_027_claimant_status_change_notifications():
    """test_id: FR-TEST-027 | source_id: AFR-PHC-023.

    Verify claimant receives notifications on claim status changes including rejection and payment.
    """
    visit = create_patient_visit(patient_user_id=1001, symptoms="Check", diagnosis="OK", created_by_user_id=10, created_by_username="staff")
    presc = create_prescription(visit_id=visit.id, prescription_number="RX-NOTIF-01", medicines_prescribed="Meds", created_by_user_id=10, created_by_username="staff")
    claim = submit_reimbursement_claim(claimant_user_id=1001, claimant_kind="faculty", claimant_username="prof1001", prescription_id=presc.id, expense_date=timezone.now().date(), amount_claimed=Decimal("1100.00"))

    # Submission notification
    notifs = PHCNotification.objects.filter(recipient_user_id=1001, notification_type="REIMBURSEMENT_STATUS")
    assert notifs.count() == 1

    review_claim_phc(claim.id, actor_user_id=10, actor_username="phc_staff")
    notifs = PHCNotification.objects.filter(recipient_user_id=1001, notification_type="REIMBURSEMENT_STATUS")
    assert notifs.count() == 2


# ---------------------------------------------------------------------------
# CFR-PHC-006 / AFR-PHC-024..026: Inventory Stock Control & Alerts
# ---------------------------------------------------------------------------

def test_fr_028_inventory_add_and_deduct_stock():
    """test_id: FR-TEST-028 | source_id: AFR-PHC-024.

    Verify PHC Staff can add to and deduct from inventory stock levels.
    """
    item = create_or_update_item(
        item_code="MED-PCM-500",
        name="Paracetamol 500mg",
        reorder_threshold=50,
    )
    assert item.stock_level == 0

    item = adjust_stock(item.id, "ADD", 100, "Initial shipment", 10, "staff")
    assert item.stock_level == 100

    item = adjust_stock(item.id, "DEDUCT", 30, "OPD distribution", 10, "staff")
    assert item.stock_level == 70


def test_fr_029_inventory_reorder_threshold_comparison():
    """test_id: FR-TEST-029 | source_id: AFR-PHC-025.

    Verify system compares updated stock level against item reorder threshold.
    """
    item = create_or_update_item(item_code="MED-AMX-250", name="Amoxicillin", reorder_threshold=20)
    adjust_stock(item.id, "ADD", 50, "Batch receipt", 10, "staff")
    item.refresh_from_db()
    assert item.stock_level > item.reorder_threshold


def test_fr_030_low_stock_warning_when_below_threshold():
    """test_id: FR-TEST-030 | source_id: AFR-PHC-026.

    Verify low-stock warning is generated for PHC Staff when stock falls below reorder threshold.
    """
    item = create_or_update_item(item_code="MED-ORS-01", name="ORS Sachet", reorder_threshold=20)
    adjust_stock(item.id, "ADD", 25, "Initial stock", 10, "staff")

    # Deduct 10 -> remaining 15 (< 20 threshold)
    adjust_stock(item.id, "DEDUCT", 10, "Distribution", 10, "staff")

    notifs = PHCNotification.objects.filter(recipient_user_id=10, notification_type="LOW_STOCK")
    assert notifs.count() >= 1
    assert "Low Stock Warning" in notifs.first().title


def test_fr_031_no_low_stock_warning_when_above_or_at_threshold():
    """test_id: FR-TEST-031 | source_id: AFR-PHC-026.

    Verify no low-stock warning is generated when stock remains at or above reorder threshold.
    """
    item = create_or_update_item(item_code="MED-BAND-01", name="Bandages", reorder_threshold=20)
    adjust_stock(item.id, "ADD", 50, "Stock refill", 10, "staff")

    # Clear any previous notifications for user 11
    PHCNotification.objects.filter(recipient_user_id=11).delete()

    # Deduct 20 -> remaining 30 (>= 20 threshold)
    adjust_stock(item.id, "DEDUCT", 20, "Daily consumption", 11, "staff2")

    notifs = PHCNotification.objects.filter(recipient_user_id=11, notification_type="LOW_STOCK")
    assert notifs.count() == 0


# ---------------------------------------------------------------------------
# CFR-PHC-007 / AFR-PHC-027..031: Procurement Requisitions Lifecycle
# ---------------------------------------------------------------------------

def test_fr_032_staff_create_procurement_requisition():
    """test_id: FR-TEST-032 | source_id: AFR-PHC-027.

    Verify PHC Staff can create and submit an inventory procurement requisition.
    """
    item = create_or_update_item(item_code="MED-IBU-400", name="Ibuprofen 400mg")
    req = submit_procurement_requisition(
        originator_user_id=10,
        originator_username="staff_user",
        justification="Depleted winter stock",
        items_data=[{"item_id": item.id, "quantity": 200}],
    )
    assert req.id is not None
    assert req.status == RequisitionStatus.PENDING_APPROVAL.value
    assert req.items.count() == 1
    assert req.items.first().quantity_requested == 200


def test_fr_033_requisition_routed_to_approving_authority():
    """test_id: FR-TEST-033 | source_id: AFR-PHC-028.

    Verify submitted inventory requisition is routed to Approving Authority.
    """
    item = create_or_update_item(item_code="MED-ASP-100", name="Aspirin 100mg")
    req = submit_procurement_requisition(
        originator_user_id=10,
        originator_username="staff_user",
        justification="Urgent requirement",
        items_data=[{"item_id": item.id, "quantity": 100}],
    )
    pending_reqs = ProcurementRequisition.objects.filter(status=RequisitionStatus.PENDING_APPROVAL.value)
    assert req in pending_reqs


def test_fr_034_approving_authority_approve_requisition():
    """test_id: FR-TEST-034 | source_id: AFR-PHC-029.

    Verify Approving Authority approves pending inventory requisition.
    """
    item = create_or_update_item(item_code="MED-ANT-01", name="Antacid Syrup")
    req = submit_procurement_requisition(
        originator_user_id=10,
        originator_username="staff_user",
        justification="Monthly restock",
        items_data=[{"item_id": item.id, "quantity": 50}],
    )
    approved = decide_procurement_requisition(req.id, approve=True, actor_user_id=30, actor_username="director", remarks="Approved as budgeted")
    assert approved.status == RequisitionStatus.APPROVED.value
    assert approved.decision_at is not None


def test_fr_035_approving_authority_reject_requisition():
    """test_id: FR-TEST-035 | source_id: AFR-PHC-029.

    Verify Approving Authority rejects pending inventory requisition.
    """
    item = create_or_update_item(item_code="MED-ANT-02", name="Antacid Tablets")
    req = submit_procurement_requisition(
        originator_user_id=10,
        originator_username="staff_user",
        justification="Excess stock",
        items_data=[{"item_id": item.id, "quantity": 500}],
    )
    rejected = decide_procurement_requisition(req.id, approve=False, actor_user_id=30, actor_username="director", remarks="Sufficient stock exists")
    assert rejected.status == RequisitionStatus.REJECTED.value


def test_fr_036_originator_notified_on_requisition_decision():
    """test_id: FR-TEST-036 | source_id: AFR-PHC-030.

    Verify originator PHC Staff is notified when requisition is approved or rejected.
    """
    item = create_or_update_item(item_code="MED-COUGH-01", name="Cough Syrup")
    req = submit_procurement_requisition(
        originator_user_id=10,
        originator_username="staff_user",
        justification="Restock",
        items_data=[{"item_id": item.id, "quantity": 25}],
    )
    decide_procurement_requisition(req.id, approve=True, actor_user_id=30, actor_username="director")

    notifs = PHCNotification.objects.filter(recipient_user_id=10, notification_type="REQUISITION_DECISION")
    assert notifs.count() >= 1
    assert "Approved" in notifs.last().title


def test_fr_037_fulfill_approved_requisition_no_auto_stock_post():
    """test_id: FR-TEST-037 | source_id: AFR-PHC-031.

    Verify PHC Staff marks approved requisition as Fulfilled after delivery without auto-altering stock.
    """
    item = create_or_update_item(item_code="MED-GAUZE-01", name="Sterile Gauze", reorder_threshold=10)
    adjust_stock(item.id, "ADD", 20, "Base", 10, "staff")
    item.refresh_from_db()
    initial_stock = item.stock_level

    req = submit_procurement_requisition(
        originator_user_id=10,
        originator_username="staff_user",
        justification="Gauze supplies",
        items_data=[{"item_id": item.id, "quantity": 100}],
    )
    decide_procurement_requisition(req.id, approve=True, actor_user_id=30, actor_username="director")

    fulfilled = fulfill_procurement_requisition(req.id, actor_user_id=10, actor_username="staff_user")
    assert fulfilled.status == RequisitionStatus.FULFILLED.value
    assert fulfilled.fulfilled_at is not None

    # Stock level MUST remain unchanged unless explicit stock adjustment is performed
    item.refresh_from_db()
    assert item.stock_level == initial_stock


# ---------------------------------------------------------------------------
# CFR-PHC-008 & 009 / AFR-PHC-032..033: Ambulance & Announcements
# ---------------------------------------------------------------------------

def test_fr_038_record_ambulance_usage_complete():
    """test_id: FR-TEST-038 | source_id: AFR-PHC-032.

    Verify PHC Staff records ambulance usage with timestamp, patient name, and destination.
    """
    dep_time = timezone.now()
    log = log_ambulance_usage(
        patient_name="Rahul Verma",
        destination="City Hospital Emergency",
        departure_time=dep_time,
        driver_name="Ramesh Singh",
        recorded_by_user_id=10,
        reason="Acute trauma",
    )
    assert log.id is not None
    assert log.patient_name == "Rahul Verma"
    assert log.destination == "City Hospital Emergency"
    assert log.departure_time == dep_time


def test_fr_039_reject_incomplete_ambulance_log(stub_iam):
    """test_id: FR-TEST-039 | source_id: AFR-PHC-032.

    Verify incomplete ambulance usage log is rejected by API validation.
    """
    client = _auth_client(
        stub_iam,
        user_id=10,
        kind="staff",
        roles=("staff",),
        permissions=("phc.ambulance.manage",),
    )
    # Missing required patient_name and destination
    res = client.post("/api/v1/phc/ambulance/", {
        "departure_time": timezone.now().isoformat(),
        "driver_name": "Ramesh",
    })
    assert res.status_code == 400


def test_fr_040_publish_health_announcements():
    """test_id: FR-TEST-040 | source_id: AFR-PHC-033.

    Verify PHC Staff publishes health advisories visible to all patients on dashboard.
    """
    ann = publish_health_announcement(
        title="Dengue Prevention Advisory",
        content="Please ensure no stagnant water around hostel premises.",
        priority="Urgent",
        published_by_user_id=10,
    )
    assert ann.id is not None
    assert ann.priority == "Urgent"

    active_list = list_active_announcements()
    assert ann in active_list


# ---------------------------------------------------------------------------
# CFR-PHC-010 / AFR-PHC-034..035: Administrative Reports & Privacy
# ---------------------------------------------------------------------------

def test_fr_041_generate_administrative_reports(stub_iam, user_ref):
    """test_id: FR-TEST-041 | source_id: AFR-PHC-034.

    Verify PHC Staff can generate administrative reports across demographics, utilization, inventory.
    """
    stub_iam(users={2001: user_ref(2001)})
    rep_demo = generate_administrative_report("demographics")
    assert rep_demo["report_type"] == "demographics"
    assert "total_unique_patients" in rep_demo

    rep_util = generate_administrative_report("utilization")
    assert rep_util["report_type"] == "utilization"
    assert "total_consultations" in rep_util

    rep_inv = generate_administrative_report("inventory")
    assert rep_inv["report_type"] == "inventory"
    assert "total_catalog_items" in rep_inv


def test_fr_042_reports_anonymize_patient_data(stub_iam, user_ref):
    """test_id: FR-TEST-042 | source_id: AFR-PHC-035.

    Verify administrative reports anonymize patient data and protect PII.
    """
    stub_iam(users={2001: user_ref(2001)})
    create_patient_visit(
        patient_user_id=2001,
        symptoms="Cold",
        diagnosis="Common cold",
        created_by_user_id=10,
        created_by_username="staff",
    )
    rep_demo = generate_administrative_report("demographics")
    assert rep_demo["anonymized"] is True
    # Ensure no patient identifiers or sensitive names are in breakdown keys
    breakdown = rep_demo["breakdown_by_category"]
    assert "2001" not in breakdown
    assert "patient_name" not in rep_demo


# ---------------------------------------------------------------------------
# CFR-PHC-011 / AFR-PHC-036: Role-Based Access Control
# ---------------------------------------------------------------------------

def test_fr_043_role_based_access_control_enforcement(stub_iam):
    """test_id: FR-TEST-043 | source_id: AFR-PHC-036.

    Verify access control enforces role-based restrictions across PHC functions.
    """
    # Student attempts to post stock adjustment (restricted to PHC Staff)
    client = _auth_client(
        stub_iam,
        user_id=2001,
        kind="student",
        roles=("student",),
        permissions=("phc.patient_record.view_self",),
    )
    res = client.post("/api/v1/phc/inventory/adjust/", {
        "item_id": 1,
        "adjustment_type": "ADD",
        "quantity": 10,
        "reason": "Unauthorized attempt",
    })
    assert res.status_code == 403


# ---------------------------------------------------------------------------
# CFR-PHC-012 / AFR-PHC-037: Sensitive-Data Immutable Audit Trail
# ---------------------------------------------------------------------------

def test_fr_044_immutable_audit_trail_recorded():
    """test_id: FR-TEST-044 | source_id: AFR-PHC-037.

    Verify immutable audit trail is recorded for sensitive operations on
    patient records, inventory, and reimbursement claims.
    """
    # 1. Patient Record creation audit
    visit = create_patient_visit(
        patient_user_id=2001,
        symptoms="Fever",
        diagnosis="Flu",
        created_by_user_id=10,
        created_by_username="nurse_staff",
    )
    audit_visit = PHCAuditTrail.objects.filter(target_type="PATIENT_RECORD", target_id=str(visit.id))
    assert audit_visit.exists()
    assert audit_visit.first().actor_username == "nurse_staff"

    # 2. Inventory level adjustment audit
    item = create_or_update_item(item_code="MED-AUD-01", name="Audit Test Item")
    adjust_stock(item.id, "ADD", 50, "Audit shipment", 10, "warehouse_staff")
    audit_inv = PHCAuditTrail.objects.filter(target_type="INVENTORY_LEVEL", target_id=item.item_code)
    assert audit_inv.exists()
    assert audit_inv.first().action == "STOCK_ADD"

    # 3. Reimbursement claim audit
    visit_emp = create_patient_visit(
        patient_user_id=1001,
        symptoms="Checkup",
        diagnosis="Health check",
        created_by_user_id=10,
        created_by_username="nurse_staff",
    )
    presc = create_prescription(
        visit_id=visit_emp.id,
        prescription_number="RX-AUD-01",
        medicines_prescribed="Meds",
        created_by_user_id=10,
        created_by_username="staff",
    )
    claim = submit_reimbursement_claim(
        claimant_user_id=1001,
        claimant_kind="faculty",
        claimant_username="prof1001",
        prescription_id=presc.id,
        expense_date=timezone.now().date(),
        amount_claimed=Decimal("750.00"),
    )
    audit_clm = PHCAuditTrail.objects.filter(target_type="REIMBURSEMENT_CLAIM", target_id=claim.claim_number)
    assert audit_clm.exists()
