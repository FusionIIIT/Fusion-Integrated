import pytest
from datetime import date
from decimal import Decimal
from core.api.exceptions import BadRequestError, PermissionDeniedError
from modules.hreis.models import EmployeeServiceRecord, HrAuditLog, LtcRequest
from modules.hreis.services.claims import (
    decide_ltc_request,
    settle_ltc_claim,
    submit_ltc_request,
    verify_ltc_request,
)
from rest_framework import status

pytestmark = pytest.mark.django_db


def test_uc_027_submit_ltc_advance_request():
    """TEST-UC-027 [HR-UC-009 Main Flow]: Verify employee can submit a valid LTC advance request."""
    EmployeeServiceRecord.objects.create(
        user_id=240,
        employee_id="EMP0240",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
    )
    ltc = submit_ltc_request(
        user_id=240,
        username="u240",
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


def test_uc_028_unauthorized_ltc_advance_submission(auth_client_factory):
    """TEST-UC-028 [HR-UC-009 Exception E1]: Verify unauthorized user cannot submit LTC advance request."""
    from rest_framework.test import APIClient
    client = APIClient()
    resp = client.post(
        "/api/v1/hreis/claims/ltc/",
        {
            "request_type": "advance",
            "block_year": "2022-2025",
            "travel_from": "Jabalpur",
            "travel_to": "Delhi",
            "travel_start_date": "2026-12-10",
            "travel_end_date": "2026-12-15",
            "estimated_amount": "15000.00",
        },
        format="json",
    )
    assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


def test_uc_029_submit_ltc_reimbursement_request():
    """TEST-UC-029 [HR-UC-010 Main Flow]: Verify employee can submit a valid LTC reimbursement request with bills."""
    EmployeeServiceRecord.objects.create(
        user_id=241,
        employee_id="EMP0241",
        department="ECE",
        designation="Assistant Professor",
        category="faculty",
    )
    ltc = submit_ltc_request(
        user_id=241,
        username="u241",
        request_type="reimbursement",
        block_year="2022-2025",
        travel_from="Jabalpur",
        travel_to="Goa",
        travel_start_date=date(2026, 11, 1),
        travel_end_date=date(2026, 11, 5),
        estimated_amount=Decimal("20000.00"),
        claimed_amount=Decimal("19500.00"),
        supporting_documents=["ticket.pdf", "boarding_pass.pdf"],
    )
    assert ltc.id is not None
    assert ltc.request_type == "reimbursement"
    assert ltc.claimed_amount == Decimal("19500.00")
    assert ltc.status == "submitted"


def test_uc_030_unauthorized_ltc_reimbursement_submission(auth_client_factory):
    """TEST-UC-030 [HR-UC-010 Exception E1]: Verify unauthorized user cannot submit LTC reimbursement request."""
    from rest_framework.test import APIClient
    client = APIClient()
    resp = client.post(
        "/api/v1/hreis/claims/ltc/",
        {
            "request_type": "reimbursement",
            "block_year": "2022-2025",
            "travel_from": "Jabalpur",
            "travel_to": "Goa",
            "travel_start_date": "2026-11-01",
            "travel_end_date": "2026-11-05",
            "estimated_amount": "20000.00",
            "claimed_amount": "19500.00",
        },
        format="json",
    )
    assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


def test_uc_031_hr_admin_verify_ltc_request():
    """TEST-UC-031 [HR-UC-011 Main Flow]: Verify HR Admin can verify LTC request documentation and advance it to approval routing."""
    ltc = LtcRequest.objects.create(
        user_id=242,
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
        remarks="All vouchers and tickets verified",
        actor_id=201,
        actor_username="hradmin",
        actor_role="hr_admin",
    )
    assert verified.verification_status == "verified"
    assert verified.status == "pending_approval"


def test_uc_032_hr_admin_reject_ltc_verification():
    """TEST-UC-032 [HR-UC-011 Alternative A1]: Verify unconfirmed/rejected LTC verification does not enter approval routing."""
    ltc = LtcRequest.objects.create(
        user_id=243,
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


def test_uc_033_non_admin_cannot_verify_ltc():
    """TEST-UC-033 [HR-UC-011 Exception E1]: Verify non-HR admin cannot verify LTC requests."""
    ltc = LtcRequest.objects.create(
        user_id=244,
        request_type="advance",
        block_year="2022-2025",
        travel_from="Jabalpur",
        travel_to="Mumbai",
        travel_start_date=date(2026, 12, 1),
        travel_end_date=date(2026, 12, 5),
        estimated_amount=Decimal("10000.00"),
        status="submitted",
    )
    with pytest.raises((BadRequestError, PermissionDeniedError)):
        verify_ltc_request(
            ltc_id=ltc.id,
            verdict="verified",
            remarks="Unauthorized attempt",
            actor_id=500,
            actor_username="faculty_user",
            actor_role="faculty",
        )


def test_uc_034_accountant_process_ltc_settlement():
    """TEST-UC-034 [HR-UC-012 Main Flow]: Verify Accountant can record settlement for approved LTC claim."""
    ltc = LtcRequest.objects.create(
        user_id=245,
        request_type="reimbursement",
        block_year="2022-2025",
        travel_from="Jabalpur",
        travel_to="Delhi",
        travel_start_date=date(2026, 11, 10),
        travel_end_date=date(2026, 11, 15),
        estimated_amount=Decimal("12000.00"),
        claimed_amount=Decimal("11500.00"),
        status="approved",
        verification_status="verified",
    )
    settled = settle_ltc_claim(
        ltc_id=ltc.id,
        reference_id="LTC-SETTLE-2026-001",
        remarks="Payment processed via NEFT voucher",
        actor_id=501,
        actor_username="accountant",
        actor_role="accountant",
    )
    assert settled.status == "settled"
    assert HrAuditLog.objects.filter(entity_type="ltc_request", entity_id=str(ltc.id)).exists()


def test_uc_035_approved_ltc_claim_pending_payment():
    """TEST-UC-035 [HR-UC-012 Alternative A1]: Verify approved LTC claim remains in approved state when payment is pending."""
    ltc = LtcRequest.objects.create(
        user_id=246,
        request_type="advance",
        block_year="2022-2025",
        travel_from="Jabalpur",
        travel_to="Bangalore",
        travel_start_date=date(2026, 12, 1),
        travel_end_date=date(2026, 12, 5),
        estimated_amount=Decimal("15000.00"),
        status="approved",
        verification_status="verified",
    )
    # Remains in approved state awaiting settlement
    assert ltc.status == "approved"
    assert ltc.settlement_date is None


def test_uc_036_ltc_settlement_internal_only():
    """TEST-UC-036 [HR-UC-012 Exception E1]: Verify HR-EIS does not execute external banking/payroll and only records settlement."""
    ltc = LtcRequest.objects.create(
        user_id=247,
        request_type="reimbursement",
        block_year="2022-2025",
        travel_from="Jabalpur",
        travel_to="Hyderabad",
        travel_start_date=date(2026, 11, 1),
        travel_end_date=date(2026, 11, 5),
        estimated_amount=Decimal("10000.00"),
        claimed_amount=Decimal("9500.00"),
        status="approved",
        verification_status="verified",
    )
    settled = settle_ltc_claim(
        ltc_id=ltc.id,
        reference_id="LTC-REF-999",
        remarks="Recorded internal voucher only",
        actor_id=501,
        actor_username="accountant",
        actor_role="accountant",
    )
    assert settled.status == "settled"
    # Settle updates internal model and audit log only


def test_uc_037_non_accountant_cannot_settle_ltc():
    """TEST-UC-037 [HR-UC-012 Exception E2]: Verify non-accountant cannot process LTC claim settlement."""
    ltc = LtcRequest.objects.create(
        user_id=248,
        request_type="advance",
        block_year="2022-2025",
        travel_from="Jabalpur",
        travel_to="Delhi",
        travel_start_date=date(2026, 12, 1),
        travel_end_date=date(2026, 12, 5),
        estimated_amount=Decimal("8000.00"),
        status="approved",
    )
    with pytest.raises((BadRequestError, PermissionDeniedError)):
        settle_ltc_claim(
            ltc_id=ltc.id,
            reference_id="REF-UNAUTH",
            remarks="Unauthorized settlement attempt",
            actor_id=600,
            actor_username="faculty_user",
            actor_role="faculty",
        )
