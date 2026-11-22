from datetime import date, timedelta
from decimal import Decimal
from django.utils import timezone
import pytest

from modules.phc.domain.entities import ReimbursementStatus, RequisitionStatus
from modules.phc.domain.errors import IneligibleClaimantError
from modules.phc.models.ambulance import AmbulanceLog
from modules.phc.models.audit import PHCAuditTrail
from modules.phc.models.doctors import Doctor, DoctorAttendance, DoctorSchedule
from modules.phc.models.inventory import InventoryItem, InventoryStockAdjustment, ProcurementRequisition
from modules.phc.models.notifications import PHCNotification
from modules.phc.models.patient_records import PatientVisit, Prescription
from modules.phc.models.reimbursement import ReimbursementClaim
from modules.phc.selectors.doctors import get_patient_doctor_availability
from modules.phc.services.ambulance import log_ambulance_usage
from modules.phc.services.doctors import create_doctor, create_or_update_schedule, mark_attendance
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

pytestmark = pytest.mark.django_db


def test_doctor_and_attendance_lifecycle():
    doc = create_doctor(
        name="A. K. Sharma",
        specialization="General Medicine",
        contact_phone="+91-9876543210",
        email="dr.sharma@iiitdmj.ac.in",
        is_visiting=False,
    )
    assert doc.id is not None

    # Add schedule
    sch = create_or_update_schedule(
        doctor_id=doc.id,
        day_of_week="Monday",
        start_time="09:00",
        end_time="13:00",
        room_number="OPD-2",
        is_published=True,
    )
    assert sch.is_published

    # Mark attendance
    att = mark_attendance(
        doctor_id=doc.id,
        status="Available",
        marked_by_user_id=901,
        remarks="Present in OPD-2",
    )
    assert att.status == "Available"

    # Verify availability summary
    avail = get_patient_doctor_availability()
    match = next(d for d in avail if d["doctor_id"] == doc.id)
    assert match["today_attendance"]["status"] == "Available"
    assert len(match["weekly_schedule"]) == 1


def test_patient_visit_and_prescription_flow():
    visit = create_patient_visit(
        patient_user_id=1001,
        doctor_id=None,
        visit_date=date.today(),
        symptoms="High fever and severe chills",
        diagnosis="Viral infection",
        notes="Advised 3 days rest",
        created_by_user_id=901,
        created_by_username="staff_user",
    )
    assert visit.id is not None

    pres = create_prescription(
        visit_id=visit.id,
        prescription_number="RX-2026-0001",
        medicines_prescribed="Paracetamol 650mg TDS, ORS sachets",
        notes="Review after 3 days",
        created_by_user_id=901,
        created_by_username="staff_user",
    )
    assert pres.prescription_number == "RX-2026-0001"
    assert pres.patient_user_id == 1001

    # Audit trail check
    audits = PHCAuditTrail.objects.filter(target_type="PATIENT_RECORD", target_id=str(visit.id))
    assert audits.exists()


def test_reimbursement_progression_flow():
    # Setup patient visit and prescription for employee (user 2001)
    visit = create_patient_visit(
        patient_user_id=2001,
        doctor_id=None,
        visit_date=date.today() - timedelta(days=10),
        symptoms="Hypertension consultation",
        diagnosis="Essential hypertension",
        notes="Prescribed antihypertensives",
        created_by_user_id=901,
        created_by_username="staff_user",
    )
    pres = create_prescription(
        visit_id=visit.id,
        prescription_number="RX-2026-0002",
        medicines_prescribed="Amlodipine 5mg OD",
        created_by_user_id=901,
        created_by_username="staff_user",
    )

    # 1. Employee submits claim (BR-04, BR-05, BR-06 check)
    claim = submit_reimbursement_claim(
        claimant_user_id=2001,
        claimant_kind="faculty",
        claimant_username="prof_sharma",
        prescription_id=pres.id,
        expense_date=date.today() - timedelta(days=5),
        amount_claimed=Decimal("1250.00"),
        bills_document_url="https://drive.google.com/sample_bills.pdf",
        remarks="Monthly prescribed hypertension medications",
    )
    assert claim.status == ReimbursementStatus.PENDING_PHC_REVIEW.value
    assert claim.claim_number.startswith("MED-CLM-")

    # 2. PHC Staff forwards to Accounts
    claim = review_claim_phc(
        claim_id=claim.id,
        actor_user_id=901,
        actor_username="phc_staff_1",
        comments="Prescription and bill vouchers matched",
    )
    assert claim.status == ReimbursementStatus.PENDING_ACCOUNTS_VERIFICATION.value

    # 3. Accounts verifies claim
    claim = verify_claim_accounts(
        claim_id=claim.id,
        actor_user_id=902,
        actor_username="accounts_officer",
        amount_verified=Decimal("1200.00"),
        comments="Eligible claim verified up to INR 1200",
    )
    assert claim.status == ReimbursementStatus.PENDING_SANCTION.value
    assert claim.amount_approved == Decimal("1200.00")

    # 4. Approving Authority sanctions claim
    claim = decide_claim_sanction(
        claim_id=claim.id,
        approve=True,
        actor_user_id=903,
        actor_username="director_approver",
        sanctioned_amount=Decimal("1200.00"),
        comments="Sanction granted as recommended by Accounts",
    )
    assert claim.status == ReimbursementStatus.APPROVED_FOR_PAYMENT.value

    # 5. Payment processing
    claim = process_claim_payment(
        claim_id=claim.id,
        actor_user_id=902,
        actor_username="accounts_officer",
        payment_reference="NEFT-20261101-0987",
        comments="Disbursed via bank transfer",
    )
    assert claim.status == ReimbursementStatus.REIMBURSED.value

    # Verification: action history timeline recorded (SUBMIT, FORWARD, VERIFY, SANCTION, PAY)
    assert claim.history.count() == 5
    # Verification: notification created for claimant
    assert PHCNotification.objects.filter(recipient_user_id=2001).exists()


def test_reimbursement_student_ineligibility_br04():
    visit = create_patient_visit(
        patient_user_id=1001,
        doctor_id=None,
        visit_date=date.today(),
        symptoms="Cold",
        diagnosis="Common cold",
        notes="None",
        created_by_user_id=901,
        created_by_username="staff_user",
    )
    pres = create_prescription(
        visit_id=visit.id,
        prescription_number="RX-STUDENT-01",
        medicines_prescribed="Cetirizine 10mg",
        created_by_user_id=901,
        created_by_username="staff_user",
    )

    with pytest.raises(IneligibleClaimantError):
        submit_reimbursement_claim(
            claimant_user_id=1001,
            claimant_kind="student",
            claimant_username="student_rahul",
            prescription_id=pres.id,
            expense_date=date.today(),
            amount_claimed=Decimal("300.00"),
        )


def test_inventory_and_stock_adjustment_with_low_stock_notification():
    item = create_or_update_item(
        item_code="MED-PCM-500",
        name="Paracetamol 500mg",
        category="Analgesic",
        reorder_threshold=30,
        unit="Strip",
    )
    # Initial stock setup
    adjust_stock(
        item_id=item.id,
        adjustment_type="ADD",
        quantity=100,
        reason="Stock received from vendor",
        actor_user_id=901,
        actor_username="compounder_1",
    )
    item.refresh_from_db()
    assert item.stock_level == 100

    # Adjust stock down to 25 (below threshold 30) -> triggers low-stock notification
    adj = adjust_stock(
        item_id=item.id,
        adjustment_type="DEDUCT",
        quantity=75,
        reason="Dispensary weekly consumption",
        actor_user_id=901,
        actor_username="compounder_1",
    )
    assert adj.stock_level == 25

    # Check notification generated
    notif = PHCNotification.objects.filter(notification_type="LOW_STOCK").first()
    assert notif is not None
    assert "Paracetamol 500mg" in notif.message


def test_procurement_requisition_workflow():
    item = create_or_update_item(
        item_code="MED-ORS-S",
        name="ORS Oral Salts",
        category="Electrolytes",
        reorder_threshold=50,
        unit="Sachet",
    )

    req = submit_procurement_requisition(
        originator_user_id=901,
        originator_username="compounder_1",
        justification="Depleted electrolytes seasonal supply",
        items_data=[{"item_id": item.id, "quantity": 100}],
    )
    assert req.status == RequisitionStatus.PENDING_APPROVAL.value
    assert req.requisition_number.startswith("REQ-")

    # Approve requisition
    req = decide_procurement_requisition(
        requisition_id=req.id,
        approve=True,
        actor_user_id=903,
        actor_username="approver_user",
        remarks="Procurement approved",
    )
    assert req.status == RequisitionStatus.APPROVED.value

    # Fulfill requisition
    req = fulfill_procurement_requisition(
        requisition_id=req.id,
        actor_user_id=901,
        actor_username="compounder_1",
    )
    assert req.status == RequisitionStatus.FULFILLED.value
    # Domain rule check: Fulfillment does not auto-increment stock level
    item.refresh_from_db()
    assert item.stock_level == 0


def test_ambulance_dispatch_lifecycle():
    now = timezone.now()
    trip = log_ambulance_usage(
        patient_name="John Doe",
        patient_user_id=1001,
        destination="Metro Hospital, Civil Lines",
        departure_time=now,
        driver_name="Ramesh Singh",
        reason="Acute chest discomfort",
        recorded_by_user_id=901,
    )
    assert trip.id is not None
    assert trip.return_time is None

    # Update return time
    later = now + timedelta(hours=2)
    updated = log_ambulance_usage(
        log_id=trip.id,
        patient_name="John Doe",
        destination="Metro Hospital, Civil Lines",
        departure_time=trip.departure_time,
        return_time=later,
        driver_name="Ramesh Singh",
        reason="Acute chest discomfort",
        recorded_by_user_id=901,
    )
    assert updated.return_time is not None
