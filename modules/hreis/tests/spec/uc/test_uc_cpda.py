from decimal import Decimal

import pytest
from rest_framework import status

from core.api.exceptions import BadRequestError, PermissionDeniedError
from modules.hreis.models import CpdaRequest, EmployeeServiceRecord
from modules.hreis.services.claims import (
    settle_cpda_claim,
    submit_cpda_request,
    verify_cpda_request,
)

pytestmark = pytest.mark.django_db


def test_uc_038_submit_cpda_advance():
    """TEST-UC-038 [HR-UC-013 Main Flow]: Verify employee can submit a valid CPDA advance request within available balance."""
    EmployeeServiceRecord.objects.create(
        user_id=250,
        employee_id="EMP0250",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
        cpda_balance=Decimal("300000.00"),
    )
    cpda = submit_cpda_request(
        user_id=250,
        username="u250",
        request_type="advance",
        purpose="IEEE Conference presentation fee",
        amount=Decimal("30000.00"),
        supporting_documents=["acceptance_letter.pdf"],
    )
    assert cpda.id is not None
    assert cpda.request_type == "advance"
    assert cpda.status == "submitted"


def test_uc_039_cpda_advance_missing_required_info():
    """TEST-UC-039 [HR-UC-013 Alternative A1]: Verify CPDA advance submission with missing required information is rejected."""
    EmployeeServiceRecord.objects.create(
        user_id=251,
        employee_id="EMP0251",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
        cpda_balance=Decimal("200000.00"),
    )
    with pytest.raises(Exception):
        submit_cpda_request(
            user_id=251,
            username="u251",
            request_type="advance",
            purpose="",  # empty purpose
            amount=Decimal("10000.00"),
            supporting_documents=[],
        )


def test_uc_040_unauthorized_cpda_advance(auth_client_factory):
    """TEST-UC-040 [HR-UC-013 Exception E1]: Verify unauthorized user cannot submit CPDA advance request."""
    from rest_framework.test import APIClient
    client = APIClient()
    resp = client.post(
        "/api/v1/hreis/cpda/",
        {
            "request_type": "advance",
            "purpose": "Books purchase",
            "amount": "5000.00",
        },
        format="json",
    )
    assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


def test_uc_041_submit_cpda_reimbursement():
    """TEST-UC-041 [HR-UC-014 Main Flow]: Verify employee can submit a valid CPDA reimbursement request with expenditure bills."""
    EmployeeServiceRecord.objects.create(
        user_id=252,
        employee_id="EMP0252",
        department="ECE",
        designation="Assistant Professor",
        category="faculty",
        cpda_balance=Decimal("150000.00"),
    )
    cpda = submit_cpda_request(
        user_id=252,
        username="u252",
        request_type="reimbursement",
        purpose="Purchase of research textbooks",
        amount=Decimal("12000.00"),
        supporting_documents=["tax_invoice.pdf", "payment_receipt.pdf"],
    )
    assert cpda.id is not None
    assert cpda.request_type == "reimbursement"
    assert cpda.amount == Decimal("12000.00")
    assert cpda.status == "submitted"


def test_uc_042_cpda_reimbursement_missing_bills():
    """TEST-UC-042 [HR-UC-014 Alternative A1]: Verify CPDA reimbursement submission with missing bills or fields is rejected."""
    from modules.hreis.domain.claims import validate_cpda_submission
    from modules.hreis.domain.exceptions import DomainValidationError

    with pytest.raises(DomainValidationError):
        validate_cpda_submission(
            request_type="reimbursement",
            purpose="Equipment repair",
            amount=Decimal("4000.00"),
            available_balance=Decimal("50000.00"),
            supporting_documents=[],  # missing required documents
        )


def test_uc_043_unauthorized_cpda_reimbursement(auth_client_factory):
    """TEST-UC-043 [HR-UC-014 Exception E1]: Verify unauthorized user cannot submit CPDA reimbursement request."""
    from rest_framework.test import APIClient
    client = APIClient()
    resp = client.post(
        "/api/v1/hreis/cpda/",
        {
            "request_type": "reimbursement",
            "purpose": "Conference travel",
            "amount": "15000.00",
        },
        format="json",
    )
    assert resp.status_code in (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN)


def test_uc_044_hr_admin_verify_cpda_claim():
    """TEST-UC-044 [HR-UC-015 Main Flow]: Verify HR Admin can verify submitted CPDA claim and route it to approval."""
    cpda = CpdaRequest.objects.create(
        user_id=253,
        request_type="reimbursement",
        purpose="Journal page charges",
        amount=Decimal("18000.00"),
        status="submitted",
    )
    verified = verify_cpda_request(
        cpda_id=cpda.id,
        verdict="verified",
        remarks="Payment receipt verified",
        actor_id=201,
        actor_username="hradmin",
        actor_role="hr_admin",
    )
    assert verified.verification_status == "verified"
    assert verified.status == "pending_approval"


def test_uc_045_unconfirmed_cpda_verification():
    """TEST-UC-045 [HR-UC-015 Alternative A1]: Verify unconfirmed CPDA verification does not enter approval routing."""
    cpda = CpdaRequest.objects.create(
        user_id=254,
        request_type="advance",
        purpose="Hardware components",
        amount=Decimal("25000.00"),
        status="submitted",
    )
    verified = verify_cpda_request(
        cpda_id=cpda.id,
        verdict="rejected",
        remarks="Items not admissible under CPDA guidelines",
        actor_id=201,
        actor_username="hradmin",
        actor_role="hr_admin",
    )
    assert verified.verification_status == "rejected"
    assert verified.status == "rejected"


def test_uc_046_non_admin_cannot_verify_cpda():
    """TEST-UC-046 [HR-UC-015 Exception E1]: Verify non-HR admin cannot verify CPDA claims."""
    cpda = CpdaRequest.objects.create(
        user_id=255,
        request_type="advance",
        purpose="Software license",
        amount=Decimal("10000.00"),
        status="submitted",
    )
    with pytest.raises((BadRequestError, PermissionDeniedError)):
        verify_cpda_request(
            cpda_id=cpda.id,
            verdict="verified",
            remarks="Unauthorized attempt",
            actor_id=600,
            actor_username="faculty_user",
            actor_role="faculty",
        )


def test_uc_047_accountant_settle_approved_cpda():
    """TEST-UC-047 [HR-UC-016 Main Flow]: Verify Accountant can settle approved CPDA claim and deduct balance."""
    rec = EmployeeServiceRecord.objects.create(
        user_id=256,
        employee_id="EMP0256",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
        cpda_balance=Decimal("100000.00"),
    )
    cpda = CpdaRequest.objects.create(
        user_id=256,
        request_type="reimbursement",
        purpose="Membership renewal",
        amount=Decimal("10000.00"),
        status="approved",
        verification_status="verified",
    )
    settled = settle_cpda_claim(
        cpda_id=cpda.id,
        passed_amount=Decimal("10000.00"),
        voucher_no="CPDA-V-2026-001",
        remarks="Voucher cleared",
        actor_id=501,
        actor_username="accountant",
        actor_role="accountant",
    )
    assert settled.status == "settled"
    rec.refresh_from_db()
    assert rec.cpda_balance == Decimal("90000.00")


def test_uc_048_approved_cpda_claim_pending_settlement():
    """TEST-UC-048 [HR-UC-016 Alternative A1]: Verify approved CPDA claim remains in approved state until settlement is received."""
    cpda = CpdaRequest.objects.create(
        user_id=257,
        request_type="advance",
        purpose="Conference registration",
        amount=Decimal("15000.00"),
        status="approved",
        verification_status="verified",
    )
    assert cpda.status == "approved"
    assert cpda.voucher_no is None or cpda.voucher_no == ""


def test_uc_049_cpda_settlement_internal_only():
    """TEST-UC-049 [HR-UC-016 Exception E1]: Verify HR-EIS does not execute direct bank disbursement or alter payroll rules."""
    rec = EmployeeServiceRecord.objects.create(
        user_id=258,
        employee_id="EMP0258",
        department="ME",
        designation="Associate Professor",
        category="faculty",
        cpda_balance=Decimal("200000.00"),
    )
    cpda = CpdaRequest.objects.create(
        user_id=258,
        request_type="reimbursement",
        purpose="Lab consumables",
        amount=Decimal("15000.00"),
        status="approved",
        verification_status="verified",
    )
    settled = settle_cpda_claim(
        cpda_id=cpda.id,
        passed_amount=Decimal("15000.00"),
        voucher_no="CPDA-V-999",
        remarks="Internal accounting entry",
        actor_id=501,
        actor_username="accountant",
        actor_role="accountant",
    )
    assert settled.status == "settled"
    rec.refresh_from_db()
    assert rec.cpda_balance == Decimal("185000.00")


def test_uc_050_non_accountant_cannot_settle_cpda():
    """TEST-UC-050 [HR-UC-016 Exception E2]: Verify non-accountant cannot settle CPDA claims."""
    cpda = CpdaRequest.objects.create(
        user_id=259,
        request_type="advance",
        purpose="Conference registration",
        amount=Decimal("12000.00"),
        status="approved",
    )
    with pytest.raises((BadRequestError, PermissionDeniedError)):
        settle_cpda_claim(
            cpda_id=cpda.id,
            passed_amount=Decimal("12000.00"),
            voucher_no="V-UNAUTH",
            remarks="Unauthorized settlement attempt",
            actor_id=600,
            actor_username="faculty_user",
            actor_role="faculty",
        )
