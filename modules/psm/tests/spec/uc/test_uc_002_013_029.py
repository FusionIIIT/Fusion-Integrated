"""Receipt confirmation, three-way invoice matching, and payment specifications."""

from datetime import date
from decimal import Decimal

import pytest

from conftest import make_principal
from core.api.exceptions import ConflictError
from modules.psm.models import (
    GoodsReceiptNote,
    Invoice,
    PaymentTransaction,
    PsmAuditLog,
    PsmNotification,
)
from modules.psm.services import (
    approvals,
    discrepancies,
    finance,
    indents,
    policy,
    procurement,
    receipts,
    stock,
    vendors,
)

pytestmark = pytest.mark.django_db


def _actor(uid, role):
    return make_principal(
        user_id=uid,
        kind="staff" if role.startswith("deptadmin_") or role in {"ps_admin", "Accounts Admin"} else "faculty",
        active_role=role,
        roles=(role,),
        modules=("psm",),
    )


def _purchase_context(uid, *, verified=True, quantity=2):
    policy.seed_default_policy()
    employee = _actor(uid, "faculty")
    da = _actor(uid + 1, "deptadmin_cse")
    hod = _actor(uid + 2, "HOD (CSE)")
    ps = _actor(uid + 3, "ps_admin")
    indent = indents.create_indent(actor=employee, department="CSE", item_description=f"UC {uid} item",
        quantity=quantity, estimated_cost=Decimal("12000.00"), justification="Teaching lab")
    stock.check_and_reserve(actor=da, indent_id=indent.pk)
    approvals.dept_admin_review(actor=da, indent_id=indent.pk, decision="approve")
    approvals.hod_recommend(actor=hod, indent_id=indent.pk, decision="recommend")
    procurement.review_and_select_method(actor=ps, indent_id=indent.pk)
    vendor = vendors.onboard_vendor(actor=ps, name=f"UC {uid} vendor", gstin="23AABCU9603R1ZM",
        bank_account_number="1234567890", bank_ifsc="SBIN0001234", bank_name="SBI",
        compliance_documents=["GST"])
    if verified:
        vendor = vendors.verify_vendor(actor=ps, vendor_id=vendor.pk)
    po = procurement.create_and_issue_po(actor=ps, indent_id=indent.pk, vendor_id=vendor.pk,
        unit_price=Decimal("6000.00"), ordered_quantity=quantity,
        planned_delivery_date=date(2026, 12, 20))
    return employee, ps, _actor(uid + 4, "Accounts Admin"), vendor, po


def _grn(employee, po, *, received, accepted, rejected=0):
    return receipts.record_grn(actor=employee, purchase_order_id=po.pk,
        received_quantity=received, accepted_quantity=accepted, rejected_quantity=rejected)


def test_tc_002_main_psm_uc_002_main_success_scenario():
    """TC-002-MAIN; source_id: PSM-UC-002 Main Success Scenario."""
    employee, _ps, accounts, _vendor, po = _purchase_context(36001)
    grn = _grn(employee, po, received=2, accepted=2)
    confirmed = receipts.confirm_receipt(actor=employee, grn_id=grn.pk)

    assert confirmed.status == "confirmed"
    assert confirmed.confirmed_at is not None and confirmed.stock_posted
    assert PsmNotification.objects.filter(payload__grn_id=grn.pk).exists()
    assert confirmed.grn_number
    invoices = finance.submit_invoice(actor=accounts, purchase_order_id=po.pk,
        invoice_number="UC36001", billed_quantity=2, billed_amount=Decimal("12000.00"))
    assert invoices.purchase_order_id == po.pk


def test_tc_002_a1_psm_uc_002_alternative_a1():
    """TC-002-A1; source_id: PSM-UC-002 Alternative A1."""
    employee, _ps, _accounts, _vendor, po = _purchase_context(36011, quantity=5)
    grn = _grn(employee, po, received=2, accepted=2)
    confirmed = receipts.confirm_receipt(actor=employee, grn_id=grn.pk)

    assert confirmed.status == "confirmed"
    assert confirmed.accepted_quantity == 2
    assert po.ordered_quantity - confirmed.accepted_quantity == 3
    po.refresh_from_db()
    assert po.status == "partially_delivered"


def test_tc_002_a2_psm_uc_002_alternative_a2():
    """TC-002-A2; source_id: PSM-UC-002 Alternative A2."""
    employee, ps, _accounts, _vendor, po = _purchase_context(36021)
    grn = _grn(employee, po, received=2, accepted=1, rejected=1)
    case = discrepancies.report_discrepancy(actor=employee, grn_id=grn.pk,
        discrepancy_type="damage", affected_quantity=1, description="One damaged item",
        requested_resolution="replacement")

    assert case.grn_id == grn.pk
    assert case.affected_quantity == 1
    with pytest.raises(ConflictError) as refused:
        receipts.confirm_receipt(actor=employee, grn_id=grn.pk)
    assert refused.value.status_code == 409
    assert ps.user_id != employee.user_id
    assert GoodsReceiptNote.objects.get(pk=grn.pk).stock_posted is False


def test_tc_013_main_psm_uc_013_main_success_scenario():
    """TC-013-MAIN; source_id: PSM-UC-013 Main Success Scenario."""
    employee, _ps, accounts, _vendor, po = _purchase_context(36101)
    grn = _grn(employee, po, received=2, accepted=2)
    receipts.confirm_receipt(actor=employee, grn_id=grn.pk)
    invoice = finance.submit_invoice(actor=accounts, purchase_order_id=po.pk,
        invoice_number="UC36101", billed_quantity=2, billed_amount=Decimal("12000.00"))

    matched = finance.verify_invoice(actor=accounts, invoice_id=invoice.pk)
    assert matched.status == "verified"
    assert matched.eligible_amount == Decimal("12000.00")
    assert matched.verified_at is not None
    assert PsmAuditLog.objects.filter(action="invoice.verified", target_id=invoice.pk).exists()


def test_tc_013_a1_psm_uc_013_alternative_a1():
    """TC-013-A1; source_id: PSM-UC-013 Alternative A1."""
    employee, _ps, accounts, _vendor, po = _purchase_context(36111)
    grn = _grn(employee, po, received=2, accepted=2)
    receipts.confirm_receipt(actor=employee, grn_id=grn.pk)
    invoice = finance.submit_invoice(actor=accounts, purchase_order_id=po.pk,
        invoice_number="UC36111", billed_quantity=2, billed_amount=Decimal("18000.00"))

    held = finance.verify_invoice(actor=accounts, invoice_id=invoice.pk)
    assert held.status == "on_hold"
    assert held.hold_reason
    assert PsmAuditLog.objects.filter(action="invoice.held", target_id=invoice.pk).exists()


def test_tc_013_a2_psm_uc_013_alternative_a2():
    """TC-013-A2; source_id: PSM-UC-013 Alternative A2."""
    employee, ps, accounts, vendor, po = _purchase_context(36121)
    vendors.update_vendor(actor=ps, vendor_id=vendor.pk, change_reason="Bank details changed",
        bank_account_number="9999999999")
    grn = _grn(employee, po, received=2, accepted=2)
    receipts.confirm_receipt(actor=employee, grn_id=grn.pk)
    invoice = finance.submit_invoice(actor=accounts, purchase_order_id=po.pk,
        invoice_number="UC36121", billed_quantity=2, billed_amount=Decimal("12000.00"))
    held = finance.verify_invoice(actor=accounts, invoice_id=invoice.pk)
    before = PaymentTransaction.objects.count()

    with pytest.raises(ConflictError) as refused:
        finance.process_payment(actor=accounts, invoice_id=invoice.pk,
            amount=Decimal("12000.00"), payment_reference="UC-INVALID-VENDOR")
    assert refused.value.status_code == 409

    assert held.status == "on_hold"
    vendor.refresh_from_db()
    assert vendor.is_verified is False
    assert PaymentTransaction.objects.count() == before
    assert ps.user_id != accounts.user_id


def test_tc_029_main_psm_uc_029_main_success_scenario():
    """TC-029-MAIN; source_id: PSM-UC-029 Main Success Scenario."""
    employee, _ps, accounts, _vendor, po = _purchase_context(36201)
    grn = _grn(employee, po, received=2, accepted=2)
    receipts.confirm_receipt(actor=employee, grn_id=grn.pk)
    invoice = finance.submit_invoice(actor=accounts, purchase_order_id=po.pk,
        invoice_number="UC36201", billed_quantity=2, billed_amount=Decimal("12000.00"))
    finance.verify_invoice(actor=accounts, invoice_id=invoice.pk)

    payment = finance.process_payment(actor=accounts, invoice_id=invoice.pk,
        amount=Decimal("12000.00"), payment_reference="UC-PAY-36201")
    invoice.refresh_from_db()
    assert payment.status == "released"
    assert invoice.status == "paid"
    assert PsmAuditLog.objects.filter(action="payment.released", target_id=invoice.pk).exists()
    assert PsmNotification.objects.filter(topic="payment.released", payload__invoice_id=invoice.pk).exists()


def test_tc_029_a1_psm_uc_029_alternative_a1():
    """TC-029-A1; source_id: PSM-UC-029 Alternative A1."""
    employee, _ps, accounts, _vendor, po = _purchase_context(36211)
    grn = _grn(employee, po, received=2, accepted=2)
    receipts.confirm_receipt(actor=employee, grn_id=grn.pk)
    invoice = finance.submit_invoice(actor=accounts, purchase_order_id=po.pk,
        invoice_number="UC36211", billed_quantity=2, billed_amount=Decimal("12000.00"))
    held = finance.hold_invoice(actor=accounts, invoice_id=invoice.pk, reason="Awaiting approval document")

    assert held.status == "on_hold"
    assert held.hold_reason == "Awaiting approval document"
    before = PaymentTransaction.objects.count()
    with pytest.raises(ConflictError) as refused:
        finance.process_payment(actor=accounts, invoice_id=invoice.pk,
            amount=Decimal("12000.00"), payment_reference="UC-HOLD-36211")
    assert refused.value.status_code == 409
    assert PaymentTransaction.objects.count() == before


def test_tc_029_a2_psm_uc_029_alternative_a2():
    """TC-029-A2; source_id: PSM-UC-029 Alternative A2."""
    employee, _ps, accounts, _vendor, po = _purchase_context(36221)
    grn = _grn(employee, po, received=2, accepted=2)
    receipts.confirm_receipt(actor=employee, grn_id=grn.pk)
    invoice = finance.submit_invoice(actor=accounts, purchase_order_id=po.pk,
        invoice_number="UC36221", billed_quantity=2, billed_amount=Decimal("18000.00"))
    finance.verify_invoice(actor=accounts, invoice_id=invoice.pk)
    before = PaymentTransaction.objects.count()

    with pytest.raises(ConflictError) as refused:
        finance.process_payment(actor=accounts, invoice_id=invoice.pk,
            amount=Decimal("18000.00"), payment_reference="UC-MISMATCH-36221")
    assert refused.value.status_code == 409

    invoice.refresh_from_db()
    assert invoice.status == "on_hold"
    assert PaymentTransaction.objects.count() == before


def test_tc_029_a3_psm_uc_029_alternative_a3():
    """TC-029-A3; source_id: PSM-UC-029 Alternative A3."""
    employee, ps, accounts, vendor, po = _purchase_context(36231)
    vendors.update_vendor(actor=ps, vendor_id=vendor.pk, change_reason="Bank details changed",
        bank_account_number="9999999999")
    grn = _grn(employee, po, received=2, accepted=2)
    receipts.confirm_receipt(actor=employee, grn_id=grn.pk)
    invoice = finance.submit_invoice(actor=accounts, purchase_order_id=po.pk,
        invoice_number="UC36231", billed_quantity=2, billed_amount=Decimal("12000.00"))
    finance.verify_invoice(actor=accounts, invoice_id=invoice.pk)
    before = PaymentTransaction.objects.count()

    with pytest.raises(ConflictError) as refused:
        finance.process_payment(actor=accounts, invoice_id=invoice.pk,
            amount=Decimal("12000.00"), payment_reference="UC-UNVERIFIED-36231")
    assert refused.value.status_code == 409

    vendor.refresh_from_db()
    assert vendor.is_verified is False
    assert PaymentTransaction.objects.count() == before
    assert Invoice.objects.filter(pk=invoice.pk, status="on_hold").exists()
