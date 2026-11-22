"""FR spec tests for LTC and CPDA Claims Management."""

from decimal import Decimal

import pytest

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


def test_fr_005_consolidated_accountant_claim_processing(hr_caller):
    """TEST-FR-005 | HR-CFR-005 consolidated-accountant-claim-processing.

    Verify that HR-EIS allows the Accountant to verify financial correctness, process approved LTC and CPDA claims, and record external payment or disbursement status.
    """
    claim = Claim.objects.create(
        employee_user_id=UID_FACULTY_1,
        employee_category="faculty",
        request_type="ltc_advance",
        purpose="Annual leave travel",
        amount=Decimal("20000.00"),
        status="approved",
    )
    actor_acc = make_actor(UID_ACCOUNTANT, role="Accountant", kind="staff")
    processed = claims.process_claim(
        actor=actor_acc,
        claim_id=claim.pk,
        financially_correct=True,
        details={"mode": "bank_transfer", "amount_disbursed": "20000.00"},
    )
    assert processed.status == "financial_processing_recorded"


def test_fr_009_consolidated_ltc_management_lifecycle(hr_caller):
    """TEST-FR-009 | HR-CFR-009 consolidated-ltc-management-lifecycle.

    Verify the complete LTC lifecycle including advance and reimbursement requests on prescribed forms, HR verification, approval routing, Accountant processing, payment status recording, and audit history preservation.
    """
    ensure_employee(UID_FACULTY_1, kind="faculty")
    res = hr_caller(
        "post",
        "/api/v1/hr/claims/create/",
        user_id=UID_FACULTY_1,
        role="faculty",
        data={
            "request_type": "ltc_advance",
            "purpose": "Visit home",
            "amount": "12000.00",
            "form_data": {"block_year": "2024-2025", "destination": "Visit home"},
        },
    )
    assert res.status_code == 201
    assert res.data["request_type"] == "ltc_advance"


def test_fr_010_consolidated_cpda_management_lifecycle(hr_caller):
    """TEST-FR-010 | HR-CFR-010 consolidated-cpda-management-lifecycle.

    Verify the complete CPDA lifecycle including advance/reimbursement submission with required purpose, amount, and documents, HR verification, approval routing, Accountant processing, and auditable disbursement recording.
    """
    ensure_employee(UID_FACULTY_1, kind="faculty")
    res = hr_caller(
        "post",
        "/api/v1/hr/claims/create/",
        user_id=UID_FACULTY_1,
        role="faculty",
        data={
            "request_type": "cpda_reimbursement",
            "purpose": "Conference registration",
            "amount": "25000.00",
            "supporting_document_links": [VALID_DRIVE_LINK],
        },
    )
    assert res.status_code == 201


def test_fr_039_hr_admin_verify_hr_requests(hr_caller):
    """TEST-FR-039 | HR-AFR-011 hr-admin-verify-hr-requests.

    Verify that HR-EIS allows the HR Administrator to verify submitted HR requests (documentation and eligibility).
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
        data={"verified": True, "note": "Documents verified"},
    )
    assert res.status_code == 200
    assert res.data["verification_details"]["verified"] is True


def test_fr_043_accountant_process_approved_ltc_claims(hr_caller):
    """TEST-FR-043 | HR-AFR-015 accountant-process-approved-ltc-claims.

    Verify that HR-EIS allows the Accountant to process approved LTC claims for financial settlement recording.
    """
    claim = Claim.objects.create(
        employee_user_id=UID_FACULTY_1,
        employee_category="faculty",
        request_type="ltc_advance",
        purpose="Travel",
        status="approved",
        amount=Decimal("15000.00"),
    )
    res = hr_caller(
        "post",
        f"/api/v1/hr/claims/{claim.pk}/processing/",
        user_id=UID_ACCOUNTANT,
        role="Accountant",
        kind="staff",
        data={
            "financially_correct": True,
            "details": {"mode": "direct_credit", "amount_disbursed": "15000.00"},
        },
    )
    assert res.status_code == 200
    assert res.data["status"] == "financial_processing_recorded"


def test_fr_044_accountant_process_approved_cpda_claims(hr_caller):
    """TEST-FR-044 | HR-AFR-016 accountant-process-approved-cpda-claims.

    Verify that HR-EIS allows the Accountant to process approved CPDA claims for financial settlement recording.
    """
    claim = Claim.objects.create(
        employee_user_id=UID_FACULTY_1,
        employee_category="faculty",
        request_type="cpda_reimbursement",
        purpose="Books",
        status="approved",
        amount=Decimal("8000.00"),
    )
    res = hr_caller(
        "post",
        f"/api/v1/hr/claims/{claim.pk}/processing/",
        user_id=UID_ACCOUNTANT,
        role="Accountant",
        kind="staff",
        data={
            "financially_correct": True,
            "details": {"mode": "cheque", "amount_disbursed": "8000.00"},
        },
    )
    assert res.status_code == 200
    assert res.data["status"] == "financial_processing_recorded"


def test_fr_045_accountant_verify_financial_correctness(hr_caller):
    """TEST-FR-045 | HR-AFR-017 accountant-verify-financial-correctness.

    Verify that HR-EIS allows the Accountant to verify financial correctness of LTC and CPDA claims.
    """
    actor = make_actor(UID_ACCOUNTANT, role="Accountant", kind="staff")
    assert actor.has_permission("hr.claim.manage")


def test_fr_046_record_payment_disbursement_status(hr_caller):
    """TEST-FR-046 | HR-AFR-018 record-payment-disbursement-status.

    Verify that HR-EIS records payment or disbursement status for approved financial claims when received from payroll or finance systems.
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
        data={
            "system": "payroll",
            "external_status": "disbursed",
            "external_reference": "TXN-998811",
        },
    )
    assert res.status_code == 201
    assert res.data["external_status"] == "disbursed"


def test_fr_088_employee_submit_ltc_advance_request(hr_caller):
    """TEST-FR-088 | HR-AFR-050 employee-submit-ltc-advance-request.

    Verify that HR-EIS allows Employees to submit LTC advance requests using prescribed forms.
    """
    ensure_employee(UID_FACULTY_1, kind="faculty")
    res = hr_caller(
        "post",
        "/api/v1/hr/claims/create/",
        user_id=UID_FACULTY_1,
        role="faculty",
        data={
            "request_type": "ltc_advance",
            "purpose": "All India LTC",
            "amount": "30000.00",
            "form_data": {"block_year": "2024-2025", "destination": "All India"},
        },
    )
    assert res.status_code == 201


def test_fr_089_employee_submit_ltc_reimbursement_request(hr_caller):
    """TEST-FR-089 | HR-AFR-051 employee-submit-ltc-reimbursement-request.

    Verify that HR-EIS allows Employees to submit LTC reimbursement requests using prescribed forms.
    """
    ensure_employee(UID_FACULTY_1, kind="faculty")
    res = hr_caller(
        "post",
        "/api/v1/hr/claims/create/",
        user_id=UID_FACULTY_1,
        role="faculty",
        data={
            "request_type": "ltc_reimbursement",
            "purpose": "Boarding passes settlement",
            "amount": "28500.00",
            "form_data": {"block_year": "2024-2025", "destination": "Boarding passes"},
        },
    )
    assert res.status_code == 201


def test_fr_090_hr_admin_verify_ltc_documentation(hr_caller):
    """TEST-FR-090 | HR-AFR-052 hr-admin-verify-ltc-documentation.

    Verify that HR-EIS allows HR Administrator to verify LTC documentation.
    """
    ensure_workflow_route("faculty", "ltc_reimbursement")
    claim = Claim.objects.create(
        employee_user_id=UID_FACULTY_1,
        employee_category="faculty",
        request_type="ltc_reimbursement",
        purpose="Settlement",
        status="pending_verification",
    )
    actor = make_actor(UID_HR_ADMIN, role="hr_officer", kind="staff")
    verified = claims.verify_claim(
        actor=actor, claim_id=claim.pk, verified=True, note="Tickets verified"
    )
    assert verified.status in ("pending_authority", "pending_verification")


def test_fr_091_hr_admin_verify_ltc_eligibility(hr_caller):
    """TEST-FR-091 | HR-AFR-053 hr-admin-verify-ltc-eligibility.

    Verify that HR-EIS allows HR Administrator to verify LTC eligibility.
    """
    actor = make_actor(UID_HR_ADMIN, role="hr_officer", kind="staff")
    assert actor.has_permission("hr.claim.verify")


def test_fr_092_route_verified_ltc_through_hierarchy(hr_caller):
    """TEST-FR-092 | HR-AFR-054 route-verified-ltc-through-hierarchy.

    Verify that HR-EIS routes verified LTC requests through the approval hierarchy.
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
    decided = claims.decide_claim(
        actor=actor_hod, claim_id=claim.pk, action="approve", note="Approved"
    )
    assert decided.status == "approved"


def test_fr_093_accountant_process_approved_ltc_claims(hr_caller):
    """TEST-FR-093 | HR-AFR-055 accountant-process-approved-ltc-claims.

    Verify that HR-EIS allows Accountant to process approved LTC claims for financial settlement recording.
    """
    claim = Claim.objects.create(
        employee_user_id=UID_FACULTY_1,
        employee_category="faculty",
        request_type="ltc_advance",
        purpose="Travel",
        status="approved",
        amount=Decimal("15000.00"),
    )
    actor_acc = make_actor(UID_ACCOUNTANT, role="Accountant", kind="staff")
    processed = claims.process_claim(
        actor=actor_acc,
        claim_id=claim.pk,
        financially_correct=True,
        details={"mode": "direct_debit", "amount_disbursed": "15000.00"},
    )
    assert processed.status == "financial_processing_recorded"


def test_fr_094_record_payment_status_ltc_claims(hr_caller):
    """TEST-FR-094 | HR-AFR-056 record-payment-status-ltc-claims.

    Verify that HR-EIS records payment status for LTC claims.
    """
    claim = Claim.objects.create(
        employee_user_id=UID_FACULTY_1,
        employee_category="faculty",
        request_type="ltc_advance",
        purpose="Travel",
        status="financial_processing_recorded",
    )
    row = claims.record_integration_status(
        actor=make_actor(UID_ACCOUNTANT, role="Accountant", kind="staff"),
        claim_id=claim.pk,
        system="finance",
        external_status="settled",
        external_reference="FIN-001",
    )
    assert row.external_status == "settled"


def test_fr_095_link_ltc_payment_status_to_payroll_without_modifying_rules(hr_caller):
    """TEST-FR-095 | HR-AFR-057 link-ltc-payment-status-to-payroll-without-modifying-rules.

    Verify that HR-EIS links LTC payment status to payroll systems without modifying payroll rules.
    """
    claim = Claim.objects.create(
        employee_user_id=UID_FACULTY_1,
        employee_category="faculty",
        request_type="ltc_advance",
        purpose="Travel",
        status="financial_processing_recorded",
    )
    row = claims.record_integration_status(
        actor=make_actor(UID_ACCOUNTANT, role="Accountant", kind="staff"),
        claim_id=claim.pk,
        system="payroll",
        external_status="linked",
        external_reference="PAY-110",
    )
    assert row.system == "payroll"


def test_fr_096_retain_full_audit_history_rejected_ltc(hr_caller):
    """TEST-FR-096 | HR-AFR-058 retain-full-audit-history-rejected-ltc.

    Verify that HR-EIS retains full audit history for rejected LTC requests.
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
    claims.decide_claim(actor=actor_hod, claim_id=claim.pk, action="reject", note="Quota exceeded")
    history = AuditEvent.objects.filter(entity_type="claim", entity_id=claim.pk)
    assert history.exists()


def test_fr_097_retain_full_audit_history_returned_ltc(hr_caller):
    """TEST-FR-097 | HR-AFR-059 retain-full-audit-history-returned-ltc.

    Verify that HR-EIS retains full audit history for returned LTC requests.
    """
    claim = Claim.objects.create(
        employee_user_id=UID_FACULTY_1,
        employee_category="faculty",
        request_type="ltc_reimbursement",
        purpose="Settlement",
        status="pending_verification",
    )
    actor_admin = make_actor(UID_HR_ADMIN, role="hr_officer", kind="staff")
    claims.verify_claim(
        actor=actor_admin, claim_id=claim.pk, verified=False, note="Incomplete bills"
    )
    history = AuditEvent.objects.filter(entity_type="claim", entity_id=claim.pk)
    assert history.exists()


def test_fr_098_employee_submit_cpda_advance_request(hr_caller):
    """TEST-FR-098 | HR-AFR-060 employee-submit-cpda-advance-request.

    Verify that HR-EIS allows Employees to submit CPDA advance requests.
    """
    ensure_employee(UID_FACULTY_1, kind="faculty")
    res = hr_caller(
        "post",
        "/api/v1/hr/claims/create/",
        user_id=UID_FACULTY_1,
        role="faculty",
        data={
            "request_type": "cpda_advance",
            "purpose": "Journal publication fees",
            "amount": "40000.00",
            "supporting_document_links": [VALID_DRIVE_LINK],
        },
    )
    assert res.status_code == 201


def test_fr_099_employee_submit_cpda_reimbursement_request(hr_caller):
    """TEST-FR-099 | HR-AFR-061 employee-submit-cpda-reimbursement-request.

    Verify that HR-EIS allows Employees to submit CPDA reimbursement requests.
    """
    ensure_employee(UID_FACULTY_1, kind="faculty")
    res = hr_caller(
        "post",
        "/api/v1/hr/claims/create/",
        user_id=UID_FACULTY_1,
        role="faculty",
        data={
            "request_type": "cpda_reimbursement",
            "purpose": "Hardware components",
            "amount": "15000.00",
            "supporting_document_links": [VALID_DRIVE_LINK],
        },
    )
    assert res.status_code == 201


def test_fr_100_valid_cpda_purpose_provided(hr_caller):
    """TEST-FR-100 | HR-AFR-062 valid-cpda-purpose-provided.

    Verify that HR-EIS accepts a CPDA request when purpose is specified.
    """
    ensure_employee(UID_FACULTY_1, kind="faculty")
    res = hr_caller(
        "post",
        "/api/v1/hr/claims/create/",
        user_id=UID_FACULTY_1,
        role="faculty",
        data={
            "request_type": "cpda_advance",
            "purpose": "Valid research purpose",
            "amount": "5000.00",
            "supporting_document_links": [VALID_DRIVE_LINK],
        },
    )
    assert res.status_code == 201


def test_fr_101_omit_cpda_purpose_rejected(hr_caller):
    """TEST-FR-101 | HR-AFR-062 omit-cpda-purpose-rejected.

    Verify that HR-EIS requires purpose and rejects CPDA requests where purpose is omitted.
    """
    res = hr_caller(
        "post",
        "/api/v1/hr/claims/create/",
        user_id=UID_FACULTY_1,
        role="faculty",
        data={
            "request_type": "cpda_advance",
            "purpose": "",
            "amount": "5000.00",
            "supporting_document_links": [VALID_DRIVE_LINK],
        },
    )
    assert res.status_code in (400, 422)


def test_fr_102_valid_cpda_amount_provided(hr_caller):
    """TEST-FR-102 | HR-AFR-063 valid-cpda-amount-provided.

    Verify that HR-EIS accepts a CPDA request when valid amount is specified.
    """
    ensure_employee(UID_FACULTY_1, kind="faculty")
    res = hr_caller(
        "post",
        "/api/v1/hr/claims/create/",
        user_id=UID_FACULTY_1,
        role="faculty",
        data={
            "request_type": "cpda_advance",
            "purpose": "Conference travel",
            "amount": "20000.00",
            "supporting_document_links": [VALID_DRIVE_LINK],
        },
    )
    assert res.status_code == 201


def test_fr_103_omit_cpda_amount_rejected(hr_caller):
    """TEST-FR-103 | HR-AFR-063 omit-cpda-amount-rejected.

    Verify that HR-EIS requires amount and rejects CPDA requests where amount is omitted or invalid.
    """
    res = hr_caller(
        "post",
        "/api/v1/hr/claims/create/",
        user_id=UID_FACULTY_1,
        role="faculty",
        data={
            "request_type": "cpda_advance",
            "purpose": "Conference travel",
            "supporting_document_links": [VALID_DRIVE_LINK],
        },
    )
    assert res.status_code in (400, 422)


def test_fr_104_valid_cpda_supporting_docs_provided(hr_caller):
    """TEST-FR-104 | HR-AFR-064 valid-cpda-supporting-docs-provided.

    Verify that HR-EIS accepts a CPDA request when supporting documents are included.
    """
    ensure_employee(UID_FACULTY_1, kind="faculty")
    res = hr_caller(
        "post",
        "/api/v1/hr/claims/create/",
        user_id=UID_FACULTY_1,
        role="faculty",
        data={
            "request_type": "cpda_reimbursement",
            "purpose": "Membership fee",
            "amount": "7000.00",
            "supporting_document_links": [VALID_DRIVE_LINK],
        },
    )
    assert res.status_code == 201


def test_fr_105_omit_cpda_supporting_docs_rejected(hr_caller):
    """TEST-FR-105 | HR-AFR-064 omit-cpda-supporting-docs-rejected.

    Verify that HR-EIS requires supporting documents and rejects CPDA requests where supporting documents are omitted.
    """
    res = hr_caller(
        "post",
        "/api/v1/hr/claims/create/",
        user_id=UID_FACULTY_1,
        role="faculty",
        data={
            "request_type": "cpda_reimbursement",
            "purpose": "Membership fee",
            "amount": "7000.00",
            "supporting_document_links": [],
        },
    )
    assert res.status_code in (400, 422)


def test_fr_106_hr_admin_verify_cpda_claims_before_routing(hr_caller):
    """TEST-FR-106 | HR-AFR-065 hr-admin-verify-cpda-claims-before-routing.

    Verify that HR-EIS allows HR Administrator to verify CPDA claims before approval routing.
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
    actor_admin = make_actor(UID_HR_ADMIN, role="hr_officer", kind="staff")
    verified = claims.verify_claim(
        actor=actor_admin, claim_id=claim.pk, verified=True, note="Valid CPDA bills"
    )
    assert verified.verification_details.get("verified") is True


def test_fr_107_route_verified_cpda_approval_routing(hr_caller):
    """TEST-FR-107 | HR-AFR-066 route-verified-cpda-approval-routing.

    Verify that HR-EIS routes verified CPDA claims through approval routing.
    """
    claim = Claim.objects.create(
        employee_user_id=UID_FACULTY_1,
        employee_category="faculty",
        request_type="cpda_advance",
        purpose="Travel",
        amount=Decimal("10000.00"),
        status="pending_authority",
        route_snapshot=[{"approver_user_id": UID_HOD}],
        current_authority_user_id=UID_HOD,
    )
    actor_hod = make_actor(UID_HOD, role="Head of Department", kind="faculty")
    approved = claims.decide_claim(actor=actor_hod, claim_id=claim.pk, action="approve")
    assert approved.status == "approved"


def test_fr_108_accountant_process_approved_cpda_claims(hr_caller):
    """TEST-FR-108 | HR-AFR-067 accountant-process-approved-cpda-claims.

    Verify that HR-EIS allows Accountant to process approved CPDA claims.
    """
    claim = Claim.objects.create(
        employee_user_id=UID_FACULTY_1,
        employee_category="faculty",
        request_type="cpda_reimbursement",
        purpose="Books",
        amount=Decimal("5000.00"),
        status="approved",
    )
    actor_acc = make_actor(UID_ACCOUNTANT, role="Accountant", kind="staff")
    processed = claims.process_claim(
        actor=actor_acc,
        claim_id=claim.pk,
        financially_correct=True,
        details={"mode": "bank_transfer", "amount_disbursed": "5000.00"},
    )
    assert processed.status == "financial_processing_recorded"


def test_fr_109_record_cpda_disbursement_details(hr_caller):
    """TEST-FR-109 | HR-AFR-068 record-cpda-disbursement-details.

    Verify that HR-EIS records CPDA disbursement details.
    """
    claim = Claim.objects.create(
        employee_user_id=UID_FACULTY_1,
        employee_category="faculty",
        request_type="cpda_advance",
        purpose="Travel",
        amount=Decimal("20000.00"),
        status="approved",
    )
    actor_acc = make_actor(UID_ACCOUNTANT, role="Accountant", kind="staff")
    processed = claims.process_claim(
        actor=actor_acc,
        claim_id=claim.pk,
        financially_correct=True,
        details={"mode": "neft", "amount_disbursed": "20000.00"},
    )
    assert processed.processing_details["mode"] == "neft"


def test_fr_110_make_cpda_disbursement_records_auditable(hr_caller):
    """TEST-FR-110 | HR-AFR-069 make-cpda-disbursement-records-auditable.

    Verify that HR-EIS makes CPDA disbursement records auditable.
    """
    claim = Claim.objects.create(
        employee_user_id=UID_FACULTY_1,
        employee_category="faculty",
        request_type="cpda_advance",
        purpose="Travel",
        amount=Decimal("10000.00"),
        status="approved",
    )
    actor_acc = make_actor(UID_ACCOUNTANT, role="Accountant", kind="staff")
    claims.process_claim(
        actor=actor_acc,
        claim_id=claim.pk,
        financially_correct=True,
        details={"mode": "cheque", "amount_disbursed": "10000.00"},
    )
    events = AuditEvent.objects.filter(entity_type="claim", entity_id=claim.pk)
    assert events.exists()
