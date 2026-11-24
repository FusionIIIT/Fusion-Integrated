# Real-thread concurrency tests against Postgres with Barrier (Step 5.7).
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal

import pytest
from django.db import IntegrityError, connection

from conftest import make_principal
from core.api.exceptions import ConflictError
from modules.psm.models import PaymentTransaction, StockReservation
from modules.psm.services import (
    approvals,
    finance,
    indents,
    policy,
    procurement,
    receipts,
    stock,
    vendors,
)

pytestmark = pytest.mark.django_db(transaction=True)


def test_concurrent_stock_reservations_never_overcommit():
    # BR-PSM-013, AFR-PSM-015, AFR-PSM-016
    policy.seed_default_policy()
    p_ps = make_principal(user_id=5001, kind="staff", active_role="ps_admin", roles=("ps_admin",))
    p_emp = make_principal(user_id=5002, kind="faculty", active_role="faculty", roles=("faculty",))
    p_da = make_principal(
        user_id=5003, kind="staff", active_role="deptadmin_cse", roles=("deptadmin_cse",)
    )
    item = stock.create_stock_item(actor=p_ps, sku="CONC-SW1", name="Switch")
    loc = stock.create_stock_location(
        actor=p_ps, code="CSE-CONC", name="CSE Store", department="CSE"
    )
    stock.record_adjustment(
        actor=p_ps,
        item_id=item.pk,
        location_id=loc.pk,
        quantity_delta=5,
        reason="Opening",
        entry_type="opening",
    )
    ind1 = indents.create_indent(
        actor=p_emp,
        department="CSE",
        item_id=item.pk,
        item_description="Switch",
        quantity=4,
        estimated_cost=Decimal("4000.00"),
        justification="A",
    )
    ind2 = indents.create_indent(
        actor=p_emp,
        department="CSE",
        item_id=item.pk,
        item_description="Switch",
        quantity=4,
        estimated_cost=Decimal("4000.00"),
        justification="B",
    )

    barrier = threading.Barrier(2)

    def _run(ind_id: int) -> str:
        try:
            barrier.wait()
            ind, _ = stock.check_and_reserve(actor=p_da, indent_id=ind_id)
            return ind.status
        finally:
            connection.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = sorted(pool.map(_run, [ind1.pk, ind2.pk]))
    assert results == ["external_required", "stock_reserved"]
    assert StockReservation.objects.filter(item=item, status="active").count() == 1


def test_concurrent_full_payments_only_release_once():
    # BR-PSM-017, BR-PSM-022
    policy.seed_default_policy()
    p_emp = make_principal(user_id=5010, kind="faculty", active_role="faculty", roles=("faculty",))
    p_da = make_principal(
        user_id=5011, kind="staff", active_role="deptadmin_cse", roles=("deptadmin_cse",)
    )
    p_hod = make_principal(
        user_id=5012, kind="faculty", active_role="HOD (CSE)", roles=("HOD (CSE)",)
    )
    p_ps = make_principal(user_id=5013, kind="staff", active_role="ps_admin", roles=("ps_admin",))
    p_acc = make_principal(
        user_id=5014, kind="staff", active_role="Accounts Admin", roles=("Accounts Admin",)
    )

    v = vendors.onboard_vendor(
        actor=p_ps,
        name="PayCo",
        gstin="23AABCU9603R1ZM",
        bank_account_number="1234567890",
        bank_ifsc="SBIN0001234",
        bank_name="SBI",
        compliance_documents=["GST"],
    )
    vendors.verify_vendor(actor=p_ps, vendor_id=v.pk)
    ind = indents.create_indent(
        actor=p_emp,
        department="CSE",
        item_description="Meter",
        quantity=2,
        estimated_cost=Decimal("2000.00"),
        justification="Lab",
    )
    stock.check_and_reserve(actor=p_da, indent_id=ind.pk)
    approvals.dept_admin_review(actor=p_da, indent_id=ind.pk, decision="approve")
    approvals.hod_recommend(actor=p_hod, indent_id=ind.pk, decision="recommend")
    procurement.review_and_select_method(actor=p_ps, indent_id=ind.pk)
    po = procurement.create_and_issue_po(
        actor=p_ps,
        indent_id=ind.pk,
        vendor_id=v.pk,
        unit_price=Decimal("1000.00"),
        planned_delivery_date=date(2026, 12, 1),
    )
    grn = receipts.record_grn(
        actor=p_emp, purchase_order_id=po.pk, received_quantity=2, accepted_quantity=2
    )
    receipts.confirm_receipt(actor=p_emp, grn_id=grn.pk)
    inv = finance.submit_invoice(
        actor=p_acc,
        purchase_order_id=po.pk,
        invoice_number="INV-CONC-1",
        billed_quantity=2,
        billed_amount=Decimal("2000.00"),
    )
    finance.verify_invoice(actor=p_acc, invoice_id=inv.pk)

    barrier = threading.Barrier(2)

    def _pay(idx: int) -> str:
        try:
            barrier.wait()
            finance.process_payment(
                actor=p_acc,
                invoice_id=inv.pk,
                amount=Decimal("2000.00"),
                payment_reference=f"PAY-CONC-{idx}",
            )
        except (ConflictError, IntegrityError):
            return "refused"
        else:
            return "ok"
        finally:
            connection.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = sorted(pool.map(_pay, [1, 2]))
    assert outcomes == ["ok", "refused"]
    assert PaymentTransaction.objects.filter(invoice=inv, status="released").count() == 1
