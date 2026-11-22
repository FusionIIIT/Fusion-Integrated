import pytest
from datetime import date
from decimal import Decimal
from core.api.exceptions import BadRequestError
from modules.hreis.models import CpdaRequest, EmployeeServiceRecord, HrAuditLog, LtcRequest
from modules.hreis.services.claims import (
    decide_cpda_request,
    decide_ltc_request,
    settle_cpda_claim,
    settle_ltc_claim,
    submit_cpda_request,
    submit_ltc_request,
    verify_cpda_request,
    verify_ltc_request,
)

pytestmark = pytest.mark.django_db


def test_br_025_ltc_advance_form():
    """TEST-BR-025 [BR-HR-016 Advance Type]: Verify LTC Advance request type is supported with required travel block information."""
    EmployeeServiceRecord.objects.create(
        user_id=380,
        employee_id="EMP0380",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
    )
    ltc = submit_ltc_request(
        user_id=380,
        username="u380",
        request_type="advance",
        block_year="2022-2025",
        travel_from="Jabalpur",
        travel_to="Delhi",
        travel_start_date=date(2026, 12, 10),
        travel_end_date=date(2026, 12, 15),
        estimated_amount=Decimal("15000.00"),
    )
    assert ltc.request_type == "advance"
    assert ltc.status == "submitted"


def test_br_026_ltc_reimbursement_form():
    """TEST-BR-026 [BR-HR-016 Reimbursement Type]: Verify LTC Reimbursement request type is supported with claimed amount and bills."""
    EmployeeServiceRecord.objects.create(
        user_id=381,
        employee_id="EMP0381",
        department="ECE",
        designation="Assistant Professor",
        category="faculty",
    )
    ltc = submit_ltc_request(
        user_id=381,
        username="u381",
        request_type="reimbursement",
        block_year="2022-2025",
        travel_from="Jabalpur",
        travel_to="Goa",
        travel_start_date=date(2026, 11, 1),
        travel_end_date=date(2026, 11, 5),
        estimated_amount=Decimal("20000.00"),
        claimed_amount=Decimal("19500.00"),
        supporting_documents=["ticket.pdf"],
    )
    assert ltc.request_type == "reimbursement"
    assert ltc.claimed_amount == Decimal("19500.00")


def test_br_027_ltc_verification_permitted():
    """TEST-BR-027 [BR-HR-017 Permitted Verification]: Verify HR Administrator verifies LTC documentation and eligibility before approval routing."""
    ltc = LtcRequest.objects.create(
        user_id=382,
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
        remarks="Tickets verified",
        actor_id=201,
        actor_username="hradmin",
        actor_role="hr_admin",
    )
    assert verified.verification_status == "verified"
    assert verified.status == "pending_approval"


def test_br_028_ltc_verification_rejected():
    """TEST-BR-028 [BR-HR-017 Prohibited Verification]: Verify rejected verification prevents LTC request from entering approval routing."""
    ltc = LtcRequest.objects.create(
        user_id=383,
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
        remarks="Quota exhausted",
        actor_id=201,
        actor_username="hradmin",
        actor_role="hr_admin",
    )
    assert verified.verification_status == "rejected"
    assert verified.status == "rejected"


def test_br_029_ltc_settlement_by_accountant():
    """TEST-BR-029 [BR-HR-018 Settlement]: Verify approved LTC claim is processed and settled by Accountant."""
    ltc = LtcRequest.objects.create(
        user_id=384,
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
        passed_amount=Decimal("11500.00"),
        reference_id="LTC-SETTLE-001",
        remarks="Settled",
        actor_id=501,
        actor_username="accountant",
        actor_role="accountant",
    )
    assert settled.status == "settled"


def test_br_030_cpda_required_information_permitted():
    """TEST-BR-030 [BR-HR-020 Permitted Information]: Verify CPDA request with purpose, amount, and supporting documents is accepted."""
    EmployeeServiceRecord.objects.create(
        user_id=385,
        employee_id="EMP0385",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
        cpda_balance=Decimal("300000.00"),
    )
    cpda = submit_cpda_request(
        user_id=385,
        username="u385",
        request_type="advance",
        purpose="Conference registration",
        amount=Decimal("20000.00"),
        supporting_documents=["invitation.pdf"],
    )
    assert cpda.id is not None
    assert cpda.status == "submitted"


def test_br_031_cpda_amount_boundary_prohibited(auth_client_factory):
    """TEST-BR-031 [BR-HR-020 Prohibited Amount]: Verify CPDA request with non-positive amount is rejected."""
    EmployeeServiceRecord.objects.create(
        user_id=386,
        employee_id="EMP0386",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
        cpda_balance=Decimal("100000.00"),
    )
    client, _ = auth_client_factory(user_id=386, role="faculty")
    resp = client.post(
        "/api/v1/hreis/cpda/",
        {"request_type": "advance", "purpose": "Conference travel", "amount": "-100.00"},
        format="json",
    )
    assert resp.status_code == 400


def test_br_032_cpda_missing_documents_prohibited():
    """TEST-BR-032 [BR-HR-020 Missing Documents]: Verify CPDA reimbursement request without supporting documents is rejected."""
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


def test_br_033_cpda_verification_permitted():
    """TEST-BR-033 [BR-HR-021 Permitted Verification]: Verify HR Admin verifies CPDA claim before approval routing."""
    cpda = CpdaRequest.objects.create(
        user_id=387,
        request_type="advance",
        purpose="Publication fee",
        amount=Decimal("15000.00"),
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
    assert verified.verification_status == "verified"
    assert verified.status == "pending_approval"


def test_br_034_cpda_verification_rejected():
    """TEST-BR-034 [BR-HR-021 Prohibited Verification]: Verify unverified CPDA claim does not enter approval routing."""
    cpda = CpdaRequest.objects.create(
        user_id=388,
        request_type="advance",
        purpose="Gadget",
        amount=Decimal("25000.00"),
        status="submitted",
    )
    verified = verify_cpda_request(
        cpda_id=cpda.id,
        verdict="rejected",
        remarks="Inadmissible expense",
        actor_id=201,
        actor_username="hradmin",
        actor_role="hr_admin",
    )
    assert verified.verification_status == "rejected"
    assert verified.status == "rejected"


def test_br_035_cpda_settlement_by_accountant():
    """TEST-BR-035 [BR-HR-022 Permitted Settlement]: Verify Accountant processes approved CPDA claim and deducts balance."""
    rec = EmployeeServiceRecord.objects.create(
        user_id=389,
        employee_id="EMP0389",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
        cpda_balance=Decimal("100000.00"),
    )
    cpda = CpdaRequest.objects.create(
        user_id=389,
        request_type="reimbursement",
        purpose="Workshop registration",
        amount=Decimal("10000.00"),
        status="approved",
        verification_status="verified",
    )
    settled = settle_cpda_claim(
        cpda_id=cpda.id,
        passed_amount=Decimal("10000.00"),
        voucher_no="V-CPDA-389",
        remarks="Settled",
        actor_id=501,
        actor_username="accountant",
        actor_role="accountant",
    )
    assert settled.status == "settled"
    rec.refresh_from_db()
    assert rec.cpda_balance == Decimal("90000.00")


def test_br_055_claim_correctness_verification_settlement():
    """TEST-BR-055 [BR-HR-035 Correctness Verification]: Verify Accountant specifies passed amount and voucher details during settlement."""
    rec = EmployeeServiceRecord.objects.create(
        user_id=390,
        employee_id="EMP0390",
        department="ECE",
        designation="Assistant Professor",
        category="faculty",
        cpda_balance=Decimal("80000.00"),
    )
    cpda = CpdaRequest.objects.create(
        user_id=390,
        request_type="reimbursement",
        purpose="Journal page charges",
        amount=Decimal("12000.00"),
        status="approved",
        verification_status="verified",
    )
    settled = settle_cpda_claim(
        cpda_id=cpda.id,
        passed_amount=Decimal("11000.00"),  # partial passed amount verified
        voucher_no="V-VERIF-390",
        remarks="Passed 11000 after checking receipts",
        actor_id=501,
        actor_username="accountant",
        actor_role="accountant",
    )
    assert settled.passed_amount == Decimal("11000.00")
    rec.refresh_from_db()
    assert rec.cpda_balance == Decimal("69000.00")
