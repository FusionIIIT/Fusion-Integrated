import pytest
from decimal import Decimal
from modules.hreis.models import CpdaRequest, EmployeeServiceRecord, HrAuditLog
from modules.hreis.services.claims import (
    decide_cpda_request,
    settle_cpda_claim,
    submit_cpda_request,
    verify_cpda_request,
)

pytestmark = pytest.mark.django_db


def test_fr_078_submit_cpda_advance():
    """TEST-FR-078 [HR-AFR-060]: Verify HR-EIS allows Employees to submit CPDA advance requests."""
    EmployeeServiceRecord.objects.create(
        user_id=230,
        employee_id="EMP0230",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
        cpda_balance=Decimal("300000.00"),
    )
    cpda = submit_cpda_request(
        user_id=230,
        username="u230",
        request_type="advance",
        purpose="Registration fee for ACM Conference",
        amount=Decimal("25000.00"),
        supporting_documents=["invitation_letter.pdf"],
    )
    assert cpda.id is not None
    assert cpda.request_type == "advance"
    assert cpda.status == "submitted"


def test_fr_079_submit_cpda_reimbursement():
    """TEST-FR-079 [HR-AFR-061]: Verify HR-EIS allows Employees to submit CPDA reimbursement requests."""
    EmployeeServiceRecord.objects.create(
        user_id=231,
        employee_id="EMP0231",
        department="ECE",
        designation="Associate Professor",
        category="faculty",
        cpda_balance=Decimal("250000.00"),
    )
    cpda = submit_cpda_request(
        user_id=231,
        username="u231",
        request_type="reimbursement",
        purpose="IEEE Membership fee",
        amount=Decimal("12000.00"),
        supporting_documents=["membership_receipt.pdf"],
    )
    assert cpda.id is not None
    assert cpda.request_type == "reimbursement"


def test_fr_080_require_cpda_purpose(auth_client_factory):
    """TEST-FR-080 [HR-AFR-062]: Verify HR-EIS requires each CPDA request to include purpose."""
    EmployeeServiceRecord.objects.create(
        user_id=232,
        employee_id="EMP0232",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
        cpda_balance=Decimal("100000.00"),
    )
    client, _ = auth_client_factory(user_id=232, role="faculty")
    resp = client.post(
        "/api/v1/hreis/cpda/",
        {"request_type": "advance", "amount": "10000.00", "purpose": ""},
        format="json",
    )
    assert resp.status_code == 400


def test_fr_081_require_cpda_amount(auth_client_factory):
    """TEST-FR-081 [HR-AFR-063]: Verify HR-EIS requires each CPDA request to include amount."""
    EmployeeServiceRecord.objects.create(
        user_id=233,
        employee_id="EMP0233",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
        cpda_balance=Decimal("100000.00"),
    )
    client, _ = auth_client_factory(user_id=233, role="faculty")
    resp = client.post(
        "/api/v1/hreis/cpda/",
        {"request_type": "advance", "purpose": "Conference travel", "amount": "-500.00"},
        format="json",
    )
    assert resp.status_code == 400


def test_fr_082_require_cpda_supporting_documents():
    """TEST-FR-082 [HR-AFR-064]: Verify HR-EIS requires each CPDA request to include supporting documents."""
    from modules.hreis.domain.claims import validate_cpda_submission
    from modules.hreis.domain.exceptions import DomainValidationError

    with pytest.raises(DomainValidationError):
        validate_cpda_submission(
            request_type="reimbursement",
            purpose="Books purchase",
            amount=Decimal("5000.00"),
            available_balance=Decimal("50000.00"),
            supporting_documents=[],
        )


def test_fr_083_hr_admin_verify_cpda_claim():
    """TEST-FR-083 [HR-AFR-065]: Verify HR-EIS allows HR Administrator to verify CPDA claims before approval routing."""
    cpda = CpdaRequest.objects.create(
        user_id=234,
        request_type="advance",
        purpose="Journal Publication Charge",
        amount=Decimal("35000.00"),
        status="submitted",
    )
    verified = verify_cpda_request(
        cpda_id=cpda.id,
        verdict="verified",
        remarks="Invoice verified",
        actor_id=201,
        actor_username="hradmin",
        actor_role="hr_admin",
    )
    assert verified.verification_status == "verified"
    assert verified.status == "pending_approval"


def test_fr_084_route_verified_cpda_to_approval():
    """TEST-FR-084 [HR-AFR-066]: Verify HR-EIS routes verified CPDA claims through approval routing."""
    EmployeeServiceRecord.objects.create(
        user_id=235,
        employee_id="EMP0235",
        department="ME",
        designation="Assistant Professor",
        category="faculty",
    )
    cpda = CpdaRequest.objects.create(
        user_id=235,
        request_type="advance",
        purpose="Conference",
        amount=Decimal("20000.00"),
        status="submitted",
    )
    verified = verify_cpda_request(
        cpda_id=cpda.id,
        verdict="verified",
        remarks="Verified",
        actor_id=201,
        actor_username="hradmin",
        actor_role="hr_admin",
    )
    assert verified.current_authority_role in ("hod", "director")


def test_fr_085_accountant_process_approved_cpda():
    """TEST-FR-085 [HR-AFR-067]: Verify HR-EIS allows Accountant to process approved CPDA claims."""
    EmployeeServiceRecord.objects.create(
        user_id=236,
        employee_id="EMP0236",
        department="ECE",
        designation="Assistant Professor",
        category="faculty",
        cpda_balance=Decimal("50000.00"),
    )
    cpda = CpdaRequest.objects.create(
        user_id=236,
        request_type="reimbursement",
        purpose="Workshop kit",
        amount=Decimal("8000.00"),
        status="approved",
        verification_status="verified",
    )
    settled = settle_cpda_claim(
        cpda_id=cpda.id,
        passed_amount=Decimal("8000.00"),
        voucher_no="CPDA-V-102",
        remarks="Settled",
        actor_id=401,
        actor_username="accountant",
        actor_role="accountant",
    )
    assert settled.status == "settled"
    assert settled.passed_amount == Decimal("8000.00")


def test_fr_086_record_cpda_disbursement_details():
    """TEST-FR-086 [HR-AFR-068]: Verify HR-EIS records CPDA disbursement details."""
    EmployeeServiceRecord.objects.create(
        user_id=237,
        employee_id="EMP0237",
        department="ECE",
        designation="Assistant Professor",
        category="faculty",
        cpda_balance=Decimal("50000.00"),
    )
    cpda = CpdaRequest.objects.create(
        user_id=237,
        request_type="advance",
        purpose="Hardware components",
        amount=Decimal("22000.00"),
        status="approved",
        verification_status="verified",
    )
    settled = settle_cpda_claim(
        cpda_id=cpda.id,
        passed_amount=Decimal("22000.00"),
        voucher_no="CHQ-7788",
        remarks="Disbursed",
        actor_id=401,
        actor_username="accountant",
        actor_role="accountant",
    )
    assert settled.disbursement_status == "disbursed"
    assert settled.disbursement_details["voucher_no"] == "CHQ-7788"


def test_fr_087_cpda_disbursement_auditable():
    """TEST-FR-087 [HR-AFR-069]: Verify HR-EIS makes CPDA disbursement records auditable."""
    EmployeeServiceRecord.objects.create(
        user_id=238,
        employee_id="EMP0238",
        department="ECE",
        designation="Assistant Professor",
        category="faculty",
        cpda_balance=Decimal("50000.00"),
    )
    cpda = CpdaRequest.objects.create(
        user_id=238,
        request_type="advance",
        purpose="Lab consumables",
        amount=Decimal("15000.00"),
        status="approved",
        verification_status="verified",
    )
    settle_cpda_claim(
        cpda_id=cpda.id,
        passed_amount=Decimal("15000.00"),
        voucher_no="V-5544",
        remarks="Audit check",
        actor_id=401,
        actor_username="accountant",
        actor_role="accountant",
    )
    logs = HrAuditLog.objects.filter(entity_type="cpda_request", entity_id=str(cpda.id))
    assert logs.filter(action="settle_cpda_claim").exists()
