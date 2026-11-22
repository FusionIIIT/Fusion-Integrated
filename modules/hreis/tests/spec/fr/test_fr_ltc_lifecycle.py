from datetime import date
from decimal import Decimal

import pytest

from modules.hreis.models import EmployeeServiceRecord, HrAuditLog, LtcRequest
from modules.hreis.services.claims import (
    decide_ltc_request,
    settle_ltc_claim,
    submit_ltc_request,
    verify_ltc_request,
)

pytestmark = pytest.mark.django_db


def test_fr_068_submit_ltc_advance_request():
    """TEST-FR-068 [HR-AFR-050]: Verify HR-EIS allows Employees to submit LTC advance requests using prescribed forms."""
    EmployeeServiceRecord.objects.create(
        user_id=220,
        employee_id="EMP0220",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
    )
    ltc = submit_ltc_request(
        user_id=220,
        username="u220",
        request_type="advance",
        block_year="2022-2025",
        travel_from="Jabalpur",
        travel_to="Delhi",
        travel_start_date=date(2026, 12, 10),
        travel_end_date=date(2026, 12, 15),
        estimated_amount=Decimal("15000.00"),
    )
    assert ltc.id is not None
    assert ltc.request_type == "advance"
    assert ltc.status == "submitted"


def test_fr_069_submit_ltc_reimbursement_request():
    """TEST-FR-069 [HR-AFR-051]: Verify HR-EIS allows Employees to submit LTC reimbursement requests using prescribed forms."""
    EmployeeServiceRecord.objects.create(
        user_id=221,
        employee_id="EMP0221",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
    )
    ltc = submit_ltc_request(
        user_id=221,
        username="u221",
        request_type="reimbursement",
        block_year="2022-2025",
        travel_from="Jabalpur",
        travel_to="Chennai",
        travel_start_date=date(2026, 11, 1),
        travel_end_date=date(2026, 11, 6),
        estimated_amount=Decimal("18000.00"),
        claimed_amount=Decimal("17500.00"),
        supporting_documents=["ticket_receipt.pdf"],
    )
    assert ltc.id is not None
    assert ltc.request_type == "reimbursement"
    assert ltc.claimed_amount == Decimal("17500.00")


def test_fr_070_hr_admin_verify_ltc_documentation():
    """TEST-FR-070 [HR-AFR-052]: Verify HR-EIS allows HR Administrator to verify LTC documentation."""
    ltc = LtcRequest.objects.create(
        user_id=222,
        request_type="reimbursement",
        block_year="2022-2025",
        travel_from="Jabalpur",
        travel_to="Kolkata",
        travel_start_date=date(2026, 11, 10),
        travel_end_date=date(2026, 11, 15),
        estimated_amount=Decimal("14000.00"),
        claimed_amount=Decimal("13800.00"),
        status="submitted",
    )
    verified = verify_ltc_request(
        ltc_id=ltc.id,
        verdict="verified",
        remarks="Air tickets and boarding passes verified",
        actor_id=201,
        actor_username="hradmin",
        actor_role="hr_admin",
    )
    assert verified.verification_status == "verified"
    assert verified.status == "pending_approval"


def test_fr_071_hr_admin_verify_ltc_eligibility():
    """TEST-FR-071 [HR-AFR-053]: Verify HR-EIS allows HR Administrator to verify LTC eligibility."""
    ltc = LtcRequest.objects.create(
        user_id=223,
        request_type="advance",
        block_year="2022-2025",
        travel_from="Jabalpur",
        travel_to="Mumbai",
        travel_start_date=date(2026, 12, 1),
        travel_end_date=date(2026, 12, 5),
        estimated_amount=Decimal("16000.00"),
        status="submitted",
    )
    verified = verify_ltc_request(
        ltc_id=ltc.id,
        verdict="rejected",
        remarks="Block year quota exhausted",
        actor_id=201,
        actor_username="hradmin",
        actor_role="hr_admin",
    )
    assert verified.verification_status == "rejected"
    assert verified.status == "rejected"


def test_fr_072_route_verified_ltc_through_approval_hierarchy():
    """TEST-FR-072 [HR-AFR-054]: Verify HR-EIS routes verified LTC requests through the approval hierarchy."""
    EmployeeServiceRecord.objects.create(
        user_id=224,
        employee_id="EMP0224",
        department="ME",
        designation="Assistant Professor",
        category="faculty",
    )
    ltc = LtcRequest.objects.create(
        user_id=224,
        request_type="advance",
        block_year="2022-2025",
        travel_from="Jabalpur",
        travel_to="Pune",
        travel_start_date=date(2026, 12, 5),
        travel_end_date=date(2026, 12, 10),
        estimated_amount=Decimal("12000.00"),
        status="submitted",
    )
    verified = verify_ltc_request(
        ltc_id=ltc.id,
        verdict="verified",
        remarks="Verified",
        actor_id=201,
        actor_username="hradmin",
        actor_role="hr_admin",
    )
    assert verified.current_authority_role in ("hod", "registrar", "director")


def test_fr_073_accountant_process_approved_ltc():
    """TEST-FR-073 [HR-AFR-055]: Verify HR-EIS allows Accountant to process approved LTC claims for financial settlement."""
    ltc = LtcRequest.objects.create(
        user_id=225,
        request_type="advance",
        block_year="2022-2025",
        travel_from="Jabalpur",
        travel_to="Jaipur",
        travel_start_date=date(2026, 12, 12),
        travel_end_date=date(2026, 12, 16),
        estimated_amount=Decimal("14000.00"),
        status="approved",
        verification_status="verified",
    )
    settled = settle_ltc_claim(
        ltc_id=ltc.id,
        passed_amount=Decimal("14000.00"),
        reference_id="FIN-LTC-555",
        remarks="Settled",
        actor_id=401,
        actor_username="accountant",
        actor_role="accountant",
    )
    assert settled.status == "settled"
    assert settled.passed_amount == Decimal("14000.00")


def test_fr_074_record_ltc_payment_status():
    """TEST-FR-074 [HR-AFR-056]: Verify HR-EIS records payment status for LTC claims."""
    ltc = LtcRequest.objects.create(
        user_id=226,
        request_type="advance",
        block_year="2022-2025",
        travel_from="Jabalpur",
        travel_to="Ahmedabad",
        travel_start_date=date(2026, 12, 15),
        travel_end_date=date(2026, 12, 18),
        estimated_amount=Decimal("10000.00"),
        status="approved",
        verification_status="verified",
    )
    settled = settle_ltc_claim(
        ltc_id=ltc.id,
        passed_amount=Decimal("10000.00"),
        reference_id="PAY-REF-101",
        remarks="Paid",
        actor_id=401,
        actor_username="accountant",
        actor_role="accountant",
    )
    assert settled.payment_status == "paid"
    assert settled.payment_reference == "PAY-REF-101"


def test_fr_075_link_ltc_payment_to_payroll_boundary():
    """TEST-FR-075 [HR-AFR-057]: Verify HR-EIS links LTC payment status to payroll systems without modifying payroll rules."""
    ltc = LtcRequest.objects.create(
        user_id=227,
        request_type="advance",
        block_year="2022-2025",
        travel_from="Jabalpur",
        travel_to="Bhopal",
        travel_start_date=date(2026, 12, 20),
        travel_end_date=date(2026, 12, 22),
        estimated_amount=Decimal("8000.00"),
        status="approved",
        verification_status="verified",
    )
    settled = settle_ltc_claim(
        ltc_id=ltc.id,
        passed_amount=Decimal("8000.00"),
        reference_id="PAYROLL-LINK-888",
        remarks="Linked",
        actor_id=401,
        actor_username="accountant",
        actor_role="accountant",
    )
    assert settled.payment_reference == "PAYROLL-LINK-888"


def test_fr_076_audit_history_rejected_ltc():
    """TEST-FR-076 [HR-AFR-058]: Verify HR-EIS retains full audit history for rejected LTC requests."""
    ltc = LtcRequest.objects.create(
        user_id=228,
        request_type="advance",
        block_year="2022-2025",
        travel_from="Jabalpur",
        travel_to="Delhi",
        travel_start_date=date(2026, 12, 25),
        travel_end_date=date(2026, 12, 28),
        estimated_amount=Decimal("15000.00"),
        status="pending_approval",
        verification_status="verified",
        current_authority_role="hod",
    )
    rejected = decide_ltc_request(
        ltc_id=ltc.id,
        outcome="rejected",
        remarks="Budget constraint for travel",
        actor_id=302,
        actor_username="hod",
        actor_role="hod",
    )
    assert rejected.status == "rejected"
    assert any(h.get("action") == "rejected" for h in rejected.approval_history)
    logs = HrAuditLog.objects.filter(entity_type="ltc_request", entity_id=str(ltc.id))
    assert logs.filter(action="ltc_rejected").exists()


def test_fr_077_audit_history_returned_ltc():
    """TEST-FR-077 [HR-AFR-059]: Verify HR-EIS retains full audit history for returned LTC requests."""
    ltc = LtcRequest.objects.create(
        user_id=229,
        request_type="advance",
        block_year="2022-2025",
        travel_from="Jabalpur",
        travel_to="Delhi",
        travel_start_date=date(2026, 12, 25),
        travel_end_date=date(2026, 12, 28),
        estimated_amount=Decimal("15000.00"),
        status="submitted",
    )
    returned = verify_ltc_request(
        ltc_id=ltc.id,
        verdict="returned",
        remarks="Please re-upload journey tickets clearly",
        actor_id=201,
        actor_username="hradmin",
        actor_role="hr_admin",
    )
    assert returned.verification_status == "returned"
    assert returned.status == "returned"
    logs = HrAuditLog.objects.filter(entity_type="ltc_request", entity_id=str(ltc.id))
    assert logs.filter(action="verify_ltc_returned").exists()
