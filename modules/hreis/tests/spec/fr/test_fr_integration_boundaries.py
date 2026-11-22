import pytest
from datetime import date
from decimal import Decimal
from modules.hreis.contracts import get_employee_record, get_leave_balance
from modules.hreis.models import CpdaRequest, EmployeeServiceRecord, LtcRequest
from modules.hreis.services.claims import settle_cpda_claim, settle_ltc_claim

pytestmark = pytest.mark.django_db


def test_fr_102_payroll_disbursement_integration():
    """TEST-FR-102 [HR-AFR-090]: Verify HR-EIS integrates with payroll system for disbursement-status exchange."""
    ltc = LtcRequest.objects.create(
        user_id=250,
        request_type="advance",
        block_year="2022-2025",
        travel_from="Jabalpur",
        travel_to="Delhi",
        travel_start_date=date(2026, 12, 1),
        travel_end_date=date(2026, 12, 5),
        estimated_amount=Decimal("15000.00"),
        status="approved",
        verification_status="verified",
    )
    settled = settle_ltc_claim(
        ltc_id=ltc.id,
        passed_amount=Decimal("15000.00"),
        reference_id="PAYROLL-DISB-7001",
        remarks="Payroll link",
        actor_id=401,
        actor_username="accountant",
        actor_role="accountant",
    )
    assert settled.payment_reference == "PAYROLL-DISB-7001"
    assert settled.payment_status == "paid"


def test_fr_103_finance_accounting_integration():
    """TEST-FR-103 [HR-AFR-091]: Verify HR-EIS integrates with finance system for accounting-status exchange."""
    EmployeeServiceRecord.objects.create(
        user_id=251,
        employee_id="EMP0251",
        department="ECE",
        designation="Assistant Professor",
        category="faculty",
        cpda_balance=Decimal("50000.00"),
    )
    cpda = CpdaRequest.objects.create(
        user_id=251,
        request_type="reimbursement",
        purpose="Journal fee",
        amount=Decimal("10000.00"),
        status="approved",
        verification_status="verified",
    )
    settled = settle_cpda_claim(
        cpda_id=cpda.id,
        passed_amount=Decimal("10000.00"),
        voucher_no="FIN-VOUCH-901",
        remarks="Finance voucher",
        actor_id=401,
        actor_username="accountant",
        actor_role="accountant",
    )
    assert settled.disbursement_details["voucher_no"] == "FIN-VOUCH-901"
    assert settled.disbursement_status == "disbursed"


def test_fr_104_fusion_identity_and_role_consistency():
    """TEST-FR-104 [HR-AFR-092]: Verify HR-EIS integrates with other Fusion modules for identity and role consistency."""
    EmployeeServiceRecord.objects.create(
        user_id=252,
        employee_id="EMP0252",
        department="Computer Science",
        designation="Associate Professor",
        category="faculty",
        retirement_status="active",
        leave_balances={"casual": 7},
        is_active=True,
    )
    dto = get_employee_record(user_id=252)
    assert dto is not None
    assert dto.user_id == 252
    assert dto.department == "Computer Science"
    assert get_leave_balance(user_id=252, leave_type="casual") == 7


def test_fr_105_real_time_synchronization():
    """TEST-FR-105 [HR-AFR-093]: Verify HR-EIS synchronizes integration data automatically and in real time."""
    from modules.hreis.models import HrAuditLog

    EmployeeServiceRecord.objects.create(
        user_id=253,
        employee_id="EMP0253",
        department="ECE",
        designation="Assistant Professor",
        category="faculty",
        cpda_balance=Decimal("50000.00"),
    )
    cpda = CpdaRequest.objects.create(
        user_id=253,
        request_type="advance",
        purpose="Conference",
        amount=Decimal("20000.00"),
        status="approved",
        verification_status="verified",
    )
    settle_cpda_claim(
        cpda_id=cpda.id,
        passed_amount=Decimal("20000.00"),
        voucher_no="TX-9900",
        remarks="Realtime sync",
        actor_id=401,
        actor_username="accountant",
        actor_role="accountant",
    )
    audit = HrAuditLog.objects.filter(entity_type="cpda_request", entity_id=str(cpda.id)).first()
    assert audit is not None
    assert audit.action == "settle_cpda_claim"
