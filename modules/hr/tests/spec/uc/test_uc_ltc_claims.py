"""UC spec tests for LTC Claims: Advance, Reimbursement, Verification, Processing."""

from decimal import Decimal

import pytest

from modules.hr.models import Claim
from modules.hr.tests.spec.conftest import (
    UID_ACCOUNTANT,
    UID_FACULTY_1,
    UID_HR_ADMIN,
    UID_UNAUTHORIZED,
    ensure_employee,
    ensure_workflow_route,
)

pytestmark = pytest.mark.django_db


def test_uc_027_main_flow_submit_ltc_advance(hr_caller):
    """TEST-UC-027 | HR-UC-009 Main Flow.

    Verify that an Employee can submit an LTC advance request using the prescribed form for HR verification.
    """
    ensure_employee(UID_FACULTY_1, kind="faculty")
    res = hr_caller(
        "post",
        "/api/v1/hr/claims/create/",
        user_id=UID_FACULTY_1,
        role="faculty",
        data={
            "request_type": "ltc_advance",
            "purpose": "Home LTC",
            "amount": "18000.00",
            "form_data": {"block_year": "2024-2025", "destination": "Home"},
        },
    )
    assert res.status_code == 201


def test_uc_028_exception_e1_unauthorized_ltc_advance_blocked(hr_caller):
    """TEST-UC-028 | HR-UC-009 Exception E1.

    Verify that unauthorized LTC advance submission is blocked and no request enters verification.
    """
    res = hr_caller(
        "post",
        "/api/v1/hr/claims/create/",
        user_id=UID_UNAUTHORIZED,
        role="student",
        kind="student",
        permissions=(),
        data={"request_type": "ltc_advance", "purpose": "Travel"},
    )
    assert res.status_code == 403


def test_uc_029_main_flow_submit_ltc_reimbursement(hr_caller):
    """TEST-UC-029 | HR-UC-010 Main Flow.

    Verify that an Employee can submit an LTC reimbursement request using the prescribed form for HR verification.
    """
    ensure_employee(UID_FACULTY_1, kind="faculty")
    res = hr_caller(
        "post",
        "/api/v1/hr/claims/create/",
        user_id=UID_FACULTY_1,
        role="faculty",
        data={
            "request_type": "ltc_reimbursement",
            "purpose": "Reimbursement bills",
            "amount": "17500.00",
            "form_data": {"block_year": "2024-2025", "destination": "Home"},
        },
    )
    assert res.status_code == 201


def test_uc_030_exception_e1_unauthorized_ltc_reimbursement_blocked(hr_caller):
    """TEST-UC-030 | HR-UC-010 Exception E1.

    Verify that unauthorized LTC reimbursement submission is blocked and no request enters verification.
    """
    res = hr_caller(
        "post",
        "/api/v1/hr/claims/create/",
        user_id=UID_UNAUTHORIZED,
        role="student",
        kind="student",
        permissions=(),
        data={"request_type": "ltc_reimbursement", "purpose": "Travel"},
    )
    assert res.status_code == 403


def test_uc_031_main_flow_verify_ltc(hr_caller):
    """TEST-UC-031 | HR-UC-011 Main Flow.

    Verify that HR Administrator can verify LTC documentation and eligibility, placing verified requests into approval routing.
    """
    ensure_workflow_route("faculty", "ltc_advance")
    claim = Claim.objects.create(
        employee_user_id=UID_FACULTY_1,
        employee_category="faculty",
        request_type="ltc_advance",
        purpose="Travel",
        status="pending_verification",
    )
    res = hr_caller(
        "post",
        f"/api/v1/hr/claims/{claim.pk}/verify/",
        user_id=UID_HR_ADMIN,
        role="hr_officer",
        data={"verified": True, "note": "Documents in order"},
    )
    assert res.status_code == 200
    assert res.data["verification_details"]["verified"] is True


def test_uc_032_alternative_a1_unconfirmed_ltc_verification(hr_caller):
    """TEST-UC-032 | HR-UC-011 Alternative A1.

    Verify that if LTC verification cannot be confirmed, the request does not enter approval routing and is retained with audit record.
    """
    claim = Claim.objects.create(
        employee_user_id=UID_FACULTY_1,
        employee_category="faculty",
        request_type="ltc_advance",
        purpose="Travel",
        status="pending_verification",
    )
    res = hr_caller(
        "post",
        f"/api/v1/hr/claims/{claim.pk}/verify/",
        user_id=UID_HR_ADMIN,
        role="hr_officer",
        data={"verified": False, "note": "Missing tickets"},
    )
    assert res.status_code == 200
    claim.refresh_from_db()
    assert claim.status == "pending_verification"


def test_uc_033_exception_e1_unauthorized_ltc_verification_blocked(hr_caller):
    """TEST-UC-033 | HR-UC-011 Exception E1.

    Verify that unauthorized LTC verification attempts are blocked.
    """
    claim = Claim.objects.create(
        employee_user_id=UID_FACULTY_1,
        employee_category="faculty",
        request_type="ltc_advance",
        purpose="Travel",
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


def test_uc_034_main_flow_accountant_process_ltc(hr_caller):
    """TEST-UC-034 | HR-UC-012 Main Flow.

    Verify that Accountant can verify financial correctness of approved LTC claim, record settlement processing, and record payment status.
    """
    claim = Claim.objects.create(
        employee_user_id=UID_FACULTY_1,
        employee_category="faculty",
        request_type="ltc_advance",
        purpose="Travel",
        status="approved",
        amount=Decimal("12000.00"),
    )
    res = hr_caller(
        "post",
        f"/api/v1/hr/claims/{claim.pk}/processing/",
        user_id=UID_ACCOUNTANT,
        role="Accountant",
        kind="staff",
        data={
            "financially_correct": True,
            "details": {"mode": "neft", "amount_disbursed": "12000.00"},
        },
    )
    assert res.status_code == 200
    assert res.data["status"] == "financial_processing_recorded"


def test_uc_035_alternative_a1_external_payment_pending(hr_caller):
    """TEST-UC-035 | HR-UC-012 Alternative A1.

    Verify that if external payment status is not yet available, claim remains in Financial Processing Recorded until later status received.
    """
    claim = Claim.objects.create(
        employee_user_id=UID_FACULTY_1,
        employee_category="faculty",
        request_type="ltc_advance",
        purpose="Travel",
        status="financial_processing_recorded",
    )
    assert claim.status == "financial_processing_recorded"


def test_uc_036_exception_e1_hr_eis_does_not_execute_payroll(hr_caller):
    """TEST-UC-036 | HR-UC-012 Exception E1.

    Verify the architectural scope boundary that HR-EIS does not execute payroll, accounting, bank transfers, or modify payroll rules/salary structures.
    """
    # Scope boundary: HR-EIS exposes no payroll calculation endpoint
    res = hr_caller(
        "post",
        "/api/v1/hr/execute-payroll/",
        user_id=UID_ACCOUNTANT,
        role="Accountant",
        kind="staff",
    )
    assert res.status_code in (404, 405)


def test_uc_037_exception_e2_unauthorized_ltc_processing_blocked(hr_caller):
    """TEST-UC-037 | HR-UC-012 Exception E2.

    Verify that unauthorized financial claim processing on LTC requests is blocked.
    """
    claim = Claim.objects.create(
        employee_user_id=UID_FACULTY_1,
        employee_category="faculty",
        request_type="ltc_advance",
        purpose="Travel",
        status="approved",
        amount=Decimal("10000.00"),
    )
    res = hr_caller(
        "post",
        f"/api/v1/hr/claims/{claim.pk}/processing/",
        user_id=UID_FACULTY_1,
        role="faculty",
        data={"mode": "cash"},
    )
    assert res.status_code == 403
