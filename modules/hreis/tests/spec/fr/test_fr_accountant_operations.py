import pytest
from datetime import date
from decimal import Decimal
from modules.hreis.models import CpdaRequest, EmployeeServiceRecord, LtcRequest

pytestmark = pytest.mark.django_db


def test_fr_029_accountant_process_approved_ltc_claims(auth_client_factory):
    """TEST-FR-029 [HR-AFR-015]: Verify HR-EIS allows Accountant to process approved LTC claims for financial settlement."""
    ltc = LtcRequest.objects.create(
        user_id=160,
        request_type="advance",
        block_year="2022-2025",
        travel_from="Jabalpur",
        travel_to="Goa",
        travel_start_date=date(2026, 12, 10),
        travel_end_date=date(2026, 12, 15),
        estimated_amount=Decimal("20000.00"),
        status="approved",
        verification_status="verified",
    )
    client_acct, _ = auth_client_factory(user_id=401, role="accountant")
    resp = client_acct.post(
        f"/api/v1/hreis/ltc/{ltc.id}/settle/",
        {"passed_amount": "18000.00", "reference_id": "TXN-LTC-001", "remarks": "Settled by Accounts"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.data["status"] == "settled"


def test_fr_030_accountant_process_approved_cpda_claims(auth_client_factory):
    """TEST-FR-030 [HR-AFR-016]: Verify HR-EIS allows Accountant to process approved CPDA claims for financial settlement."""
    EmployeeServiceRecord.objects.create(
        user_id=161,
        employee_id="EMP0161",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
        cpda_balance=Decimal("50000.00"),
    )
    cpda = CpdaRequest.objects.create(
        user_id=161,
        request_type="reimbursement",
        purpose="IEEE Conference registration",
        amount=Decimal("15000.00"),
        status="approved",
        verification_status="verified",
    )
    client_acct, _ = auth_client_factory(user_id=401, role="accountant")
    resp = client_acct.post(
        f"/api/v1/hreis/cpda/{cpda.id}/settle/",
        {"passed_amount": "15000.00", "voucher_no": "VOUCH-001", "remarks": "Processed"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.data["status"] == "settled"


def test_fr_031_accountant_verify_financial_correctness():
    """TEST-FR-031 [HR-AFR-017]: Verify HR-EIS allows Accountant to verify financial correctness of claims."""
    from modules.hreis.domain.claims import validate_financial_settlement
    from modules.hreis.domain.exceptions import DomainValidationError

    with pytest.raises(DomainValidationError):
        validate_financial_settlement(
            passed_amount=Decimal("0.00"),
            reference_id="REF-123",
        )

    with pytest.raises(DomainValidationError):
        validate_financial_settlement(
            passed_amount=Decimal("1000.00"),
            reference_id="",
        )


def test_fr_032_record_payment_or_disbursement_status(auth_client_factory):
    """TEST-FR-032 [HR-AFR-018]: Verify HR-EIS records payment or disbursement status for approved financial claims."""
    ltc = LtcRequest.objects.create(
        user_id=162,
        request_type="advance",
        block_year="2022-2025",
        travel_from="Jabalpur",
        travel_to="Delhi",
        travel_start_date=date(2026, 12, 10),
        travel_end_date=date(2026, 12, 15),
        estimated_amount=Decimal("12000.00"),
        status="approved",
        verification_status="verified",
    )
    client_acct, _ = auth_client_factory(user_id=401, role="accountant")
    resp = client_acct.post(
        f"/api/v1/hreis/ltc/{ltc.id}/settle/",
        {"passed_amount": "12000.00", "reference_id": "BANK-REF-999", "remarks": "Paid"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.data["payment_status"] == "paid"
    assert resp.data["payment_reference"] == "BANK-REF-999"
