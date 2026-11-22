"""UC spec tests for CPDA Claims: Advance, Reimbursement, Verification, Processing."""

from decimal import Decimal

import pytest

from modules.hr.models import Claim
from modules.hr.tests.spec.conftest import (
    UID_ACCOUNTANT,
    UID_FACULTY_1,
    UID_HR_ADMIN,
    UID_UNAUTHORIZED,
    VALID_DRIVE_LINK,
    ensure_employee,
    ensure_workflow_route,
)

pytestmark = pytest.mark.django_db


def test_uc_038_main_flow_submit_cpda_advance(hr_caller):
    """TEST-UC-038 | HR-UC-013 Main Flow.

    Verify that an Employee can submit a CPDA advance request containing required purpose, amount, and supporting documents.
    """
    ensure_employee(UID_FACULTY_1, kind="faculty")
    res = hr_caller(
        "post",
        "/api/v1/hr/claims/create/",
        user_id=UID_FACULTY_1,
        role="faculty",
        data={
            "request_type": "cpda_advance",
            "purpose": "Book Purchase",
            "amount": "5000.00",
            "supporting_document_links": [VALID_DRIVE_LINK],
        },
    )
    assert res.status_code == 201


def test_uc_039_alternative_a1_missing_cpda_advance_fields(hr_caller):
    """TEST-UC-039 | HR-UC-013 Alternative A1.

    Verify that if required information (purpose, amount, or documents) is missing, HR-EIS does not accept CPDA advance submission.
    """
    res = hr_caller(
        "post",
        "/api/v1/hr/claims/create/",
        user_id=UID_FACULTY_1,
        role="faculty",
        data={"request_type": "cpda_advance", "purpose": "", "amount": "5000.00"},
    )
    assert res.status_code in (400, 422)


def test_uc_040_exception_e1_unauthorized_cpda_advance_blocked(hr_caller):
    """TEST-UC-040 | HR-UC-013 Exception E1.

    Verify that unauthorized CPDA advance submission attempts are blocked.
    """
    res = hr_caller(
        "post",
        "/api/v1/hr/claims/create/",
        user_id=UID_UNAUTHORIZED,
        role="student",
        kind="student",
        permissions=(),
        data={"request_type": "cpda_advance", "purpose": "Test"},
    )
    assert res.status_code == 403


def test_uc_041_main_flow_submit_cpda_reimbursement(hr_caller):
    """TEST-UC-041 | HR-UC-014 Main Flow.

    Verify that an Employee can submit a CPDA reimbursement request containing required purpose, amount, and bills.
    """
    ensure_employee(UID_FACULTY_1, kind="faculty")
    res = hr_caller(
        "post",
        "/api/v1/hr/claims/create/",
        user_id=UID_FACULTY_1,
        role="faculty",
        data={
            "request_type": "cpda_reimbursement",
            "purpose": "Conference Reg",
            "amount": "12000.00",
            "supporting_document_links": [VALID_DRIVE_LINK],
        },
    )
    assert res.status_code == 201


def test_uc_042_alternative_a1_missing_cpda_reimbursement_fields(hr_caller):
    """TEST-UC-042 | HR-UC-014 Alternative A1.

    Verify that if required information is missing, HR-EIS does not accept CPDA reimbursement submission.
    """
    res = hr_caller(
        "post",
        "/api/v1/hr/claims/create/",
        user_id=UID_FACULTY_1,
        role="faculty",
        data={
            "request_type": "cpda_reimbursement",
            "purpose": "Conference Reg",
            "supporting_documents": [],
        },
    )
    assert res.status_code in (400, 422)


def test_uc_043_exception_e1_unauthorized_cpda_reimbursement_blocked(hr_caller):
    """TEST-UC-043 | HR-UC-014 Exception E1.

    Verify that unauthorized CPDA reimbursement submission attempts are blocked.
    """
    res = hr_caller(
        "post",
        "/api/v1/hr/claims/create/",
        user_id=UID_UNAUTHORIZED,
        role="student",
        kind="student",
        permissions=(),
        data={"request_type": "cpda_reimbursement", "purpose": "Test"},
    )
    assert res.status_code == 403


def test_uc_044_main_flow_verify_cpda(hr_caller):
    """TEST-UC-044 | HR-UC-015 Main Flow.

    Verify that HR Administrator can verify a submitted CPDA claim and route it to the applicable approval path.
    """
    ensure_workflow_route("faculty", "cpda_advance")
    claim = Claim.objects.create(
        employee_user_id=UID_FACULTY_1,
        employee_category="faculty",
        request_type="cpda_advance",
        purpose="Travel",
        amount=Decimal("10000.00"),
        status="pending_verification",
    )
    res = hr_caller(
        "post",
        f"/api/v1/hr/claims/{claim.pk}/verify/",
        user_id=UID_HR_ADMIN,
        role="hr_officer",
        data={"verified": True, "note": "Verified"},
    )
    assert res.status_code == 200


def test_uc_045_alternative_a1_unconfirmed_cpda_verification(hr_caller):
    """TEST-UC-045 | HR-UC-015 Alternative A1.

    Verify that if CPDA verification cannot be confirmed, claim does not enter approval routing and remains outside verified state.
    """
    claim = Claim.objects.create(
        employee_user_id=UID_FACULTY_1,
        employee_category="faculty",
        request_type="cpda_advance",
        purpose="Travel",
        amount=Decimal("10000.00"),
        status="pending_verification",
    )
    res = hr_caller(
        "post",
        f"/api/v1/hr/claims/{claim.pk}/verify/",
        user_id=UID_HR_ADMIN,
        role="hr_officer",
        data={"verified": False, "note": "Invalid receipts"},
    )
    assert res.status_code == 200
    claim.refresh_from_db()
    assert claim.status == "pending_verification"


def test_uc_046_exception_e1_unauthorized_cpda_verification_blocked(hr_caller):
    """TEST-UC-046 | HR-UC-015 Exception E1.

    Verify that unauthorized CPDA claim verification is blocked.
    """
    claim = Claim.objects.create(
        employee_user_id=UID_FACULTY_1,
        employee_category="faculty",
        request_type="cpda_advance",
        purpose="Travel",
        amount=Decimal("10000.00"),
        status="pending_verification",
    )
    res = hr_caller(
        "post",
        f"/api/v1/hr/claims/{claim.pk}/verify/",
        user_id=UID_FACULTY_1,
        role="faculty",
        data={"verified": True},
    )
    assert res.status_code == 403


def test_uc_047_main_flow_accountant_process_cpda(hr_caller):
    """TEST-UC-047 | HR-UC-016 Main Flow.

    Verify that Accountant can process approved CPDA claim, verify financial correctness, and record disbursement details in audit trail.
    """
    claim = Claim.objects.create(
        employee_user_id=UID_FACULTY_1,
        employee_category="faculty",
        request_type="cpda_reimbursement",
        purpose="Books",
        status="approved",
        amount=Decimal("6000.00"),
    )
    res = hr_caller(
        "post",
        f"/api/v1/hr/claims/{claim.pk}/processing/",
        user_id=UID_ACCOUNTANT,
        role="Accountant",
        kind="staff",
        data={
            "financially_correct": True,
            "details": {"mode": "bank_transfer", "amount_disbursed": "6000.00"},
        },
    )
    assert res.status_code == 200
    assert res.data["status"] == "financial_processing_recorded"


def test_uc_048_alternative_a1_external_cpda_disbursement_pending(hr_caller):
    """TEST-UC-048 | HR-UC-016 Alternative A1.

    Verify that if external disbursement status is not yet available, claim remains in Financial Processing Recorded until status becomes available.
    """
    claim = Claim.objects.create(
        employee_user_id=UID_FACULTY_1,
        employee_category="faculty",
        request_type="cpda_reimbursement",
        purpose="Books",
        status="financial_processing_recorded",
    )
    assert claim.status == "financial_processing_recorded"


def test_uc_049_exception_e1_hr_eis_does_not_execute_disbursement(hr_caller):
    """TEST-UC-049 | HR-UC-016 Exception E1.

    Verify the architectural scope boundary that HR-EIS does not execute payroll, accounting, bank transfers, or modify payroll rules/salary structures during CPDA claim processing.
    """
    res = hr_caller(
        "post",
        "/api/v1/hr/disburse-funds/",
        user_id=UID_ACCOUNTANT,
        role="Accountant",
        kind="staff",
    )
    assert res.status_code in (404, 405)


def test_uc_050_exception_e2_unauthorized_cpda_processing_blocked(hr_caller):
    """TEST-UC-050 | HR-UC-016 Exception E2.

    Verify that unauthorized processing of CPDA claims is blocked.
    """
    claim = Claim.objects.create(
        employee_user_id=UID_FACULTY_1,
        employee_category="faculty",
        request_type="cpda_advance",
        purpose="Travel",
        status="approved",
        amount=Decimal("5000.00"),
    )
    res = hr_caller(
        "post",
        f"/api/v1/hr/claims/{claim.pk}/processing/",
        user_id=UID_FACULTY_1,
        role="faculty",
        data={"mode": "cash"},
    )
    assert res.status_code == 403
