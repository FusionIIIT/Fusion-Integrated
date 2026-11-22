from decimal import Decimal

import pytest

from core.api.exceptions import BadRequestError
from modules.hreis.models import CpdaRequest, EmployeeServiceRecord, HrAuditLog
from modules.hreis.services.claims import (
    decide_cpda_request,
    settle_cpda_claim,
    submit_cpda_request,
    verify_cpda_request,
)

pytestmark = pytest.mark.django_db


def test_wf_028_cpda_advance_approved_and_processed():
    """TEST-WF-028 [BW-HR-10 Advance Approval & Settlement Path]: Verify full workflow path for CPDA Advance from submission through verification, approval, settlement, and balance deduction."""
    rec = EmployeeServiceRecord.objects.create(
        user_id=550,
        employee_id="EMP0550",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
        cpda_balance=Decimal("200000.00"),
    )
    cpda = submit_cpda_request(
        user_id=550,
        username="u550",
        request_type="advance",
        purpose="Conference travel",
        amount=Decimal("25000.00"),
        supporting_documents=["brochure.pdf"],
    )
    assert cpda.status == "submitted"
    verified = verify_cpda_request(
        cpda_id=cpda.id,
        verdict="verified",
        remarks="Verified",
        actor_id=201,
        actor_username="hradmin",
        actor_role="hr_admin",
    )
    assert verified.status == "pending_approval"
    approved = decide_cpda_request(
        cpda_id=cpda.id,
        outcome="approved",
        remarks="Approved",
        actor_id=301,
        actor_username="hod",
        actor_role="hod",
    )
    assert approved.status == "approved"
    settled = settle_cpda_claim(
        cpda_id=cpda.id,
        passed_amount=Decimal("25000.00"),
        voucher_no="V-CPDA-ADV-550",
        remarks="Advance disbursed",
        actor_id=501,
        actor_username="accountant",
        actor_role="accountant",
    )
    assert settled.status == "settled"
    rec.refresh_from_db()
    assert rec.cpda_balance == Decimal("175000.00")


def test_wf_029_cpda_balance_guard():
    """TEST-WF-029 [BW-HR-10 CPDA Balance Guard]: Verify CPDA Advance exceeding available balance fails initial guard."""
    EmployeeServiceRecord.objects.create(
        user_id=551,
        employee_id="EMP0551",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
        cpda_balance=Decimal("20000.00"),
    )
    with pytest.raises(BadRequestError):
        submit_cpda_request(
            user_id=551,
            username="u551",
            request_type="advance",
            purpose="Exceeding expense",
            amount=Decimal("50000.00"),
            supporting_documents=["doc.pdf"],
        )


def test_wf_030_cpda_reimbursement_approved_and_processed():
    """TEST-WF-030 [BW-HR-11 Reimbursement Approval & Settlement Path]: Verify full workflow path for CPDA Reimbursement with bills through verification, approval, settlement, and deduction."""
    rec = EmployeeServiceRecord.objects.create(
        user_id=552,
        employee_id="EMP0552",
        department="ECE",
        designation="Assistant Professor",
        category="faculty",
        cpda_balance=Decimal("150000.00"),
    )
    cpda = submit_cpda_request(
        user_id=552,
        username="u552",
        request_type="reimbursement",
        purpose="Research book purchase",
        amount=Decimal("15000.00"),
        supporting_documents=["receipt.pdf"],
    )
    verify_cpda_request(
        cpda_id=cpda.id,
        verdict="verified",
        remarks="Bills verified",
        actor_id=201,
        actor_username="hradmin",
        actor_role="hr_admin",
    )
    decide_cpda_request(
        cpda_id=cpda.id,
        outcome="approved",
        remarks="Approved",
        actor_id=301,
        actor_username="hod",
        actor_role="hod",
    )
    settled = settle_cpda_claim(
        cpda_id=cpda.id,
        passed_amount=Decimal("15000.00"),
        voucher_no="V-CPDA-REIM-552",
        remarks="Reimbursement settled",
        actor_id=501,
        actor_username="accountant",
        actor_role="accountant",
    )
    assert settled.status == "settled"
    rec.refresh_from_db()
    assert rec.cpda_balance == Decimal("135000.00")


def test_wf_031_cpda_unapproved_settlement_guard():
    """TEST-WF-031 [BW-HR-11 Settlement Voucher Guard]: Verify unapproved CPDA reimbursement cannot be settled by Accountant."""
    EmployeeServiceRecord.objects.create(
        user_id=553,
        employee_id="EMP0553",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
        cpda_balance=Decimal("100000.00"),
    )
    cpda = CpdaRequest.objects.create(
        user_id=553,
        request_type="reimbursement",
        purpose="Unapproved claim",
        amount=Decimal("10000.00"),
        status="submitted",
    )
    with pytest.raises(BadRequestError):
        settle_cpda_claim(
            cpda_id=cpda.id,
            passed_amount=Decimal("10000.00"),
            voucher_no="V-553",
            remarks="Premature attempt",
            actor_id=501,
            actor_username="accountant",
            actor_role="accountant",
        )


def test_wf_032_cpda_verification_rejection():
    """TEST-WF-032 [BW-HR-12 Verification Rejection Path]: Verify CPDA claim rejected during verification terminates workflow."""
    cpda = CpdaRequest.objects.create(
        user_id=554,
        request_type="advance",
        purpose="Inadmissible item",
        amount=Decimal("10000.00"),
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
    assert verified.status == "rejected"


def test_wf_033_cpda_authority_rejection():
    """TEST-WF-033 [BW-HR-12 Authority Rejection Path]: Verify verified CPDA claim rejected by Approving Authority terminates workflow without deduction."""
    rec = EmployeeServiceRecord.objects.create(
        user_id=555,
        employee_id="EMP0555",
        department="CSE",
        designation="Assistant Professor",
        category="faculty",
        cpda_balance=Decimal("100000.00"),
    )
    cpda = CpdaRequest.objects.create(
        user_id=555,
        request_type="advance",
        purpose="Travel advance",
        amount=Decimal("20000.00"),
        status="pending_approval",
        verification_status="verified",
    )
    decided = decide_cpda_request(
        cpda_id=cpda.id,
        outcome="rejected",
        remarks="Rejected by HOD",
        actor_id=301,
        actor_username="hod",
        actor_role="hod",
    )
    assert decided.status == "rejected"
    rec.refresh_from_db()
    assert rec.cpda_balance == Decimal("100000.00")


def test_wf_034_cpda_forward_one_traversal():
    """TEST-WF-034 [BW-HR-13 Forwarding Traversal Path]: Verify verified CPDA claim forwarded through one authority traversal to final approval."""
    cpda = CpdaRequest.objects.create(
        user_id=556,
        request_type="advance",
        purpose="Major lab equipment component",
        amount=Decimal("50000.00"),
        status="pending_approval",
        verification_status="verified",
    )
    fwd = decide_cpda_request(
        cpda_id=cpda.id,
        outcome="forwarded",
        remarks="Forwarding to Director",
        actor_id=301,
        actor_username="hod",
        actor_role="hod",
    )
    assert fwd.status == "forwarded"
    approved = decide_cpda_request(
        cpda_id=cpda.id,
        outcome="approved",
        remarks="Approved by Director",
        actor_id=305,
        actor_username="director",
        actor_role="director",
    )
    assert approved.status == "approved"


def test_wf_035_cpda_forwarding_authority_guard():
    """TEST-WF-035 [BW-HR-13 Forwarding Authority Guard]: Verify non-designated authority cannot decide CPDA claim during traversal."""
    cpda = CpdaRequest.objects.create(
        user_id=557,
        request_type="advance",
        purpose="Equipment",
        amount=Decimal("40000.00"),
        status="forwarded",
        current_authority_role="director",
        verification_status="verified",
    )
    with pytest.raises(BadRequestError):
        decide_cpda_request(
            cpda_id=cpda.id,
            outcome="approved",
            remarks="Unauthorized decision",
            actor_id=999,
            actor_username="staff_user",
            actor_role="staff",
        )


def test_wf_036_cw_cpda_lifecycle_balance_consistency():
    """TEST-WF-036 [CW-HR-04 Full Lifecycle with Balance Consistency]: Verify composite CPDA lifecycle maintains balance consistency and audit logging across full lifecycle."""
    rec = EmployeeServiceRecord.objects.create(
        user_id=558,
        employee_id="EMP0558",
        department="CSE",
        designation="Professor",
        category="faculty",
        cpda_balance=Decimal("250000.00"),
    )
    cpda = submit_cpda_request(
        user_id=558,
        username="u558",
        request_type="reimbursement",
        purpose="International conference membership",
        amount=Decimal("20000.00"),
        supporting_documents=["fee_receipt.pdf"],
    )
    verify_cpda_request(
        cpda_id=cpda.id,
        verdict="verified",
        remarks="Receipts valid",
        actor_id=201,
        actor_username="hradmin",
        actor_role="hr_admin",
    )
    decide_cpda_request(
        cpda_id=cpda.id,
        outcome="approved",
        remarks="Approved",
        actor_id=301,
        actor_username="hod",
        actor_role="hod",
    )
    settled = settle_cpda_claim(
        cpda_id=cpda.id,
        passed_amount=Decimal("20000.00"),
        voucher_no="CW-CPDA-SETTLE-558",
        remarks="Full claim settled",
        actor_id=501,
        actor_username="accountant",
        actor_role="accountant",
    )
    assert settled.status == "settled"
    rec.refresh_from_db()
    assert rec.cpda_balance == Decimal("230000.00")
    assert HrAuditLog.objects.filter(entity_type="cpda_request", entity_id=str(cpda.id)).count() >= 3
