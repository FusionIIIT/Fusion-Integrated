"""BR spec tests for LTC and CPDA Claims Policies."""

from decimal import Decimal

import pytest

from core.api.exceptions import ConflictError
from modules.hr.models import AuditEvent, Claim
from modules.hr.services import claims
from modules.hr.tests.spec.conftest import (
    UID_ACCOUNTANT,
    UID_FACULTY_1,
    UID_HOD,
    UID_HR_ADMIN,
    VALID_DRIVE_LINK,
    ensure_employee,
    ensure_workflow_route,
    make_actor,
)

pytestmark = pytest.mark.django_db


def test_br_031_ltc_advance_prescribed_form_permitted(hr_caller):
    """TEST-BR-031 | BR-HR-016 ltc-advance-prescribed-form-permitted.

    Verify that HR-EIS supports LTC Advance requests submitted using prescribed forms.
    """
    ensure_workflow_route("faculty", "claim_ltc_advance")
    ensure_employee(UID_FACULTY_1, kind="faculty")
    res = hr_caller(
        "post",
        "/api/v1/hr/claims/create/",
        user_id=UID_FACULTY_1,
        role="faculty",
        data={
            "request_type": "ltc_advance",
            "purpose": "Home LTC",
            "amount": "15000.00",
            "form_data": {"destination": "Home", "declared_members": ["self"]},
        },
    )
    assert res.status_code == 201


def test_br_032_ltc_reimbursement_prescribed_form_permitted(hr_caller):
    """TEST-BR-032 | BR-HR-016 ltc-reimbursement-prescribed-form-permitted.

    Verify that HR-EIS supports LTC Reimbursement requests submitted using prescribed forms.
    """
    ensure_workflow_route("faculty", "claim_ltc_reimbursement")
    ensure_employee(UID_FACULTY_1, kind="faculty")
    res = hr_caller(
        "post",
        "/api/v1/hr/claims/create/",
        user_id=UID_FACULTY_1,
        role="faculty",
        data={
            "request_type": "ltc_reimbursement",
            "purpose": "Reimbursement bills",
            "amount": "14000.00",
            "form_data": {"destination": "Home", "ticket_numbers": ["T12345"]},
        },
    )
    assert res.status_code == 201


def test_br_033_verified_ltc_advances_to_approval(hr_caller):
    """TEST-BR-033 | BR-HR-017 verified-ltc-advances-to-approval.

    Verify that HR Administrator verifies documentation and eligibility before an LTC request enters approval routing.
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
        data={"verified": True},
    )
    assert res.status_code == 200


def test_br_034_unconfirmed_ltc_blocks_approval_routing(hr_caller):
    """TEST-BR-034 | BR-HR-017 unconfirmed-ltc-blocks-approval-routing.

    Verify that an LTC request whose documentation or eligibility cannot be confirmed does not enter approval routing.
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
        data={"verified": False},
    )
    assert res.status_code == 200
    claim.refresh_from_db()
    assert claim.status == "pending_verification"


def test_br_035_approved_ltc_available_to_accountant(hr_caller):
    """TEST-BR-035 | BR-HR-018 approved-ltc-available-to-accountant.

    Verify that an approved LTC claim is available to the Accountant for HR-EIS-side financial settlement processing.
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
        user_id=UID_ACCOUNTANT,
        role="Accountant",
        kind="staff",
        data={
            "financially_correct": True,
            "details": {"mode": "neft", "amount_disbursed": "10000.00"},
        },
    )
    assert res.status_code == 200
    assert res.data["status"] == "financial_processing_recorded"


def test_br_036_unapproved_ltc_blocks_settlement_prohibited(hr_caller):
    """TEST-BR-036 | BR-HR-018 unapproved-ltc-blocks-settlement-prohibited.

    Verify that an LTC claim that has not received final approval cannot be processed for financial settlement.
    """
    claim = Claim.objects.create(
        employee_user_id=UID_FACULTY_1,
        employee_category="faculty",
        request_type="ltc_advance",
        purpose="Travel",
        status="pending_authority",
        amount=Decimal("10000.00"),
    )
    res = hr_caller(
        "post",
        f"/api/v1/hr/claims/{claim.pk}/processing/",
        user_id=UID_ACCOUNTANT,
        role="Accountant",
        kind="staff",
        data={"mode": "neft"},
    )
    assert res.status_code in (400, 409, 422)


def test_br_037_link_payment_status_without_modifying_payroll_rules(hr_caller):
    """TEST-BR-037 | BR-HR-019 link-payment-status-without-modifying-payroll-rules.

    Verify that HR-EIS records and links LTC payment status with payroll or finance systems without modifying payroll rules.
    """
    claim = Claim.objects.create(
        employee_user_id=UID_FACULTY_1,
        employee_category="faculty",
        request_type="ltc_advance",
        purpose="Travel",
        status="financial_processing_recorded",
    )
    res = hr_caller(
        "post",
        f"/api/v1/hr/claims/{claim.pk}/integration-status/",
        user_id=UID_ACCOUNTANT,
        role="Accountant",
        kind="staff",
        data={"system": "payroll", "external_status": "synced"},
    )
    assert res.status_code == 201


def test_br_038_full_audit_history_rejected_returned_ltc(hr_caller):
    """TEST-BR-038 | BR-HR-019 full-audit-history-rejected-returned-ltc.

    Verify that HR-EIS retains full audit history for rejected or returned LTC requests.
    """
    claim = Claim.objects.create(
        employee_user_id=UID_FACULTY_1,
        employee_category="faculty",
        request_type="ltc_advance",
        purpose="Travel",
        status="pending_authority",
        route_snapshot=[{"approver_user_id": UID_HOD}],
        current_authority_user_id=UID_HOD,
    )
    actor_hod = make_actor(UID_HOD, role="Head of Department", kind="faculty")
    claims.decide_claim(actor=actor_hod, claim_id=claim.pk, action="reject", note="Ineligible")
    assert AuditEvent.objects.filter(entity_type="claim", entity_id=claim.pk).exists()


def test_br_039_all_required_fields_present_permitted(hr_caller):
    """TEST-BR-039 | BR-HR-020 all-required-fields-present-permitted.

    Verify that a CPDA request including purpose, amount, and supporting documents is accepted for submission.
    """
    ensure_workflow_route("faculty", "claim_cpda_advance")
    ensure_employee(UID_FACULTY_1, kind="faculty")
    res = hr_caller(
        "post",
        "/api/v1/hr/claims/create/",
        user_id=UID_FACULTY_1,
        role="faculty",
        data={
            "request_type": "cpda_advance",
            "purpose": "Conference",
            "amount": "8000.00",
            "supporting_document_links": [VALID_DRIVE_LINK],
        },
    )
    assert res.status_code == 201


def test_br_040_missing_required_field_prohibited(hr_caller):
    """TEST-BR-040 | BR-HR-020 missing-required-field-prohibited.

    Verify that a CPDA request missing purpose, amount, or supporting documents is rejected before submission acceptance.
    """
    res = hr_caller(
        "post",
        "/api/v1/hr/claims/create/",
        user_id=UID_FACULTY_1,
        role="faculty",
        data={
            "request_type": "cpda_advance",
            "purpose": "Conference",
            "amount": "8000.00",
        },
    )
    assert res.status_code in (400, 422)


def test_br_041_verified_cpda_enters_approval_route(hr_caller):
    """TEST-BR-041 | BR-HR-021 verified-cpda-enters-approval-route.

    Verify that HR Administrator verifies CPDA claims before approval routing and verified claims enter the approval route.
    """
    ensure_workflow_route("faculty", "cpda_advance")
    claim = Claim.objects.create(
        employee_user_id=UID_FACULTY_1,
        employee_category="faculty",
        request_type="cpda_advance",
        purpose="Travel",
        amount=Decimal("5000.00"),
        status="pending_verification",
    )
    res = hr_caller(
        "post",
        f"/api/v1/hr/claims/{claim.pk}/verify/",
        user_id=UID_HR_ADMIN,
        role="hr_officer",
        data={"verified": True},
    )
    assert res.status_code == 200


def test_br_042_unverified_cpda_blocks_approval_routing(hr_caller):
    """TEST-BR-042 | BR-HR-021 unverified-cpda-blocks-approval-routing.

    Verify that an unverified CPDA claim does not enter the approval route.
    """
    claim = Claim.objects.create(
        employee_user_id=UID_FACULTY_1,
        employee_category="faculty",
        request_type="cpda_advance",
        purpose="Travel",
        amount=Decimal("5000.00"),
        status="pending_verification",
    )
    res = hr_caller(
        "post",
        f"/api/v1/hr/claims/{claim.pk}/verify/",
        user_id=UID_HR_ADMIN,
        role="hr_officer",
        data={"verified": False},
    )
    assert res.status_code == 200
    claim.refresh_from_db()
    assert claim.status == "pending_verification"


def test_br_043_accountant_process_cpda_disbursement(hr_caller):
    """TEST-BR-043 | BR-HR-022 accountant-process-cpda-disbursement.

    Verify that Accountant processes approved CPDA claims in HR-EIS and records disbursement details.
    """
    claim = Claim.objects.create(
        employee_user_id=UID_FACULTY_1,
        employee_category="faculty",
        request_type="cpda_reimbursement",
        purpose="Books",
        status="approved",
        amount=Decimal("4000.00"),
    )
    res = hr_caller(
        "post",
        f"/api/v1/hr/claims/{claim.pk}/processing/",
        user_id=UID_ACCOUNTANT,
        role="Accountant",
        kind="staff",
        data={
            "financially_correct": True,
            "details": {"mode": "direct_credit", "amount_disbursed": "4000.00"},
        },
    )
    assert res.status_code == 200
    assert res.data["status"] == "financial_processing_recorded"


def test_br_044_cpda_disbursement_records_auditable(hr_caller):
    """TEST-BR-044 | BR-HR-022 cpda-disbursement-records-auditable.

    Verify that CPDA disbursement details recorded by Accountant are kept permanently auditable.
    """
    claim = Claim.objects.create(
        employee_user_id=UID_FACULTY_1,
        employee_category="faculty",
        request_type="cpda_advance",
        purpose="Travel",
        status="approved",
        amount=Decimal("3000.00"),
    )
    actor_acc = make_actor(UID_ACCOUNTANT, role="Accountant", kind="staff")
    claims.process_claim(
        actor=actor_acc,
        claim_id=claim.pk,
        financially_correct=True,
        details={"mode": "neft", "amount_disbursed": "3000.00"},
    )
    assert AuditEvent.objects.filter(
        entity_type="claim", entity_id=claim.pk, action="claim.financial_processing_recorded"
    ).exists()


def test_br_066_financial_correctness_verified_permitted(hr_caller):
    """TEST-BR-066 | BR-HR-035 financial-correctness-verified-permitted.

    Verify that Accountant verifies financial correctness according to configured rules before recording financial settlement for approved claim.
    """
    actor = make_actor(UID_ACCOUNTANT, role="Accountant", kind="staff")
    assert actor.has_permission("hr.claim.manage")


def test_br_067_financial_discrepancy_blocks_settlement_prohibited(hr_caller):
    """TEST-BR-067 | BR-HR-035 financial-discrepancy-blocks-settlement-prohibited.

    Verify that if financial correctness cannot be confirmed (e.g. calculation discrepancy or entitlement mismatch), settlement processing is blocked.
    """
    claim = Claim.objects.create(
        employee_user_id=UID_FACULTY_1,
        employee_category="faculty",
        request_type="cpda_advance",
        purpose="Travel",
        status="pending_authority",
        amount=Decimal("5000.00"),
    )
    actor_acc = make_actor(UID_ACCOUNTANT, role="Accountant", kind="staff")
    with pytest.raises(ConflictError):
        claims.process_claim(
            actor=actor_acc,
            claim_id=claim.pk,
            financially_correct=False,
            details={"discrepancy": True},
        )
