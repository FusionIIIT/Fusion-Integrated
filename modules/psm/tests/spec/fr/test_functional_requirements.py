"""Executable functional requirement checks for the frozen FR design."""

import json
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from django.db.models import Sum
from django.utils import timezone

from conftest import make_principal
from core.api.exceptions import ConflictError, DomainError
from modules.psm import registry
from modules.psm.models import (
    DiscrepancyCommunication,
    Indent,
    IndentVersion,
    PaymentTransaction,
    PsmAuditLog,
    PsmNotification,
    PurchaseOrder,
    ReportGenerationLog,
    StockLedgerEntry,
    StockReservation,
    TenderBid,
    VendorVersion,
)
from modules.psm.services import (
    approvals,
    discrepancies,
    finance,
    indents,
    policy,
    procurement,
    receipts,
    reports,
    stock,
    tenders,
    transfers,
    vendors,
)

pytestmark = pytest.mark.django_db


def _actor(uid, role):
    return make_principal(
        user_id=uid,
        kind="faculty" if role in ("faculty", "HOD (CSE)") else "staff",
        active_role=role,
        roles=(role,),
        modules=("psm",),
        permissions=tuple(registry.ROLE_GRANTS[role]),
    )


def _ctx():
    policy.seed_default_policy()
    return (
        _actor(11001, "faculty"),
        _actor(11002, "deptadmin_cse"),
        _actor(11003, "HOD (CSE)"),
        _actor(11004, "ps_admin"),
        _actor(11005, "Director"),
        _actor(11006, "Accounts Admin"),
        _actor(11007, "Auditor"),
    )


def _indent(emp, *, desc="Test item", qty=2, cost="1000.00", item=None):
    return indents.create_indent(
        actor=emp,
        department="CSE",
        item_id=item.pk if item else None,
        item_description=desc,
        quantity=qty,
        estimated_cost=Decimal(cost),
        justification="Functional test request",
        submit=True,
    )


def _stock(ps, *, qty=20):
    item = stock.create_stock_item(
        actor=ps, sku=f"FR-{timezone.now().strftime('%H%M%S%f')}", name="Test stock", unit="unit"
    )
    loc = stock.create_stock_location(
        actor=ps,
        code=f"FR-{timezone.now().strftime('%H%M%S%f')}",
        name="CSE store",
        department="CSE",
    )
    if qty:
        stock.record_adjustment(
            actor=ps,
            item_id=item.pk,
            location_id=loc.pk,
            quantity_delta=qty,
            reason="Opening balance",
            entry_type="opening",
        )
    return item, loc


def _external_ready(emp, da, hod, ps, *, cost="40000.00", desc="External item", qty=2):
    obj = _indent(emp, desc=desc, qty=qty, cost=cost)
    stock.check_and_reserve(actor=da, indent_id=obj.pk)
    approvals.dept_admin_review(actor=da, indent_id=obj.pk, decision="approve", priority="normal")
    approvals.hod_recommend(actor=hod, indent_id=obj.pk, decision="recommend")
    procurement.review_and_select_method(actor=ps, indent_id=obj.pk)
    return obj


def _vendor(ps, *, verified=True):
    obj = vendors.onboard_vendor(
        actor=ps,
        name="Functional Vendor",
        gstin="23ABCDE1234F1Z5",
        bank_account_number="123456789012",
        bank_ifsc="SBIN0001234",
        bank_name="SBI",
        compliance_documents=["gst.pdf"],
    )
    return vendors.verify_vendor(actor=ps, vendor_id=obj.pk) if verified else obj


def _po(emp, da, hod, ps, *, qty=2, cost="40000.00", desc="PO goods", verified=True):
    indent = _external_ready(emp, da, hod, ps, cost=cost, desc=desc, qty=qty)
    vendor = _vendor(ps, verified=verified)
    po = procurement.create_and_issue_po(
        actor=ps,
        indent_id=indent.pk,
        vendor_id=vendor.pk,
        unit_price=Decimal(cost) / qty,
        ordered_quantity=qty,
        planned_delivery_date=date.today() + timedelta(days=10),
    )
    return indent, vendor, po


def _case001():
    emp, _, _, _ps, *_ = _ctx()
    obj = _indent(emp, desc="Printer toner", qty=3, cost="1500.00")
    assert obj.indent_number and obj.submitted_at and obj.quantity == 3
    assert PsmAuditLog.objects.filter(
        target_type="indent", target_id=obj.pk, action="indent.submitted"
    ).exists()
    second = _indent(emp, desc="Second item", qty=1, cost="50.00")
    assert second.indent_number != obj.indent_number


def _case002():
    emp, *_ = _ctx()
    with pytest.raises(DomainError) as refused:
        indents.create_indent(
            actor=emp,
            department="CSE",
            item_description="",
            quantity=1,
            estimated_cost=Decimal("10.00"),
            justification="Missing description",
            submit=True,
        )
    assert refused.value.status_code == 422
    assert not Indent.objects.filter(user_id=emp.user_id).exists()


def _case003():
    emp, *_ = _ctx()
    first = _indent(emp, desc="A4 paper", qty=4)
    second = _indent(emp, desc="A4 paper", qty=4)
    assert second.is_duplicate_flagged and second.duplicate_of_indent_id == first.pk


def _case004():
    emp, *_ = _ctx()
    obj = _indent(emp)
    modified = indents.modify_indent(actor=emp, indent_id=obj.pk, quantity=3)
    assert modified.quantity == 3 and modified.version == 2
    assert list(IndentVersion.objects.filter(indent=obj).values_list("version", flat=True)) == [
        2,
        1,
    ]


def _case005():
    from modules.psm.models import PsmPolicy

    emp, _da, *_ = _ctx()
    obj = _indent(emp)
    PsmPolicy.objects.filter(is_active=True).update(modifiable_states=[])
    with pytest.raises(DomainError) as refused:
        indents.modify_indent(actor=emp, indent_id=obj.pk, quantity=3)
    assert refused.value.status_code == 409
    obj.refresh_from_db()
    assert obj.quantity == 2 and obj.version == 1


def _case006():
    emp, *_ = _ctx()
    obj = _indent(emp)
    ended = indents.withdraw_indent(actor=emp, indent_id=obj.pk, reason="No longer needed")
    assert ended.status == "withdrawn"


def _case007():
    emp, *_ = _ctx()
    obj = _indent(emp)
    indents.withdraw_indent(actor=emp, indent_id=obj.pk, reason="Cancel")
    with pytest.raises(ConflictError) as refused:
        indents.withdraw_indent(actor=emp, indent_id=obj.pk, reason="Again")
    assert refused.value.status_code == 409
    obj.refresh_from_db()
    assert obj.status == "withdrawn" and obj.transitions.count() == 2


def _case008():
    pytest.skip(
        "NOT_AUTOMATED: the available edit operation submits a draft as part of saving, "
        "so the specified editable-before-submission state cannot be inspected."
    )


def _case009():
    emp, da, *_ = _ctx()
    obj = _indent(emp)
    stock.check_and_reserve(actor=da, indent_id=obj.pk)
    approvals.dept_admin_review(
        actor=da, indent_id=obj.pk, decision="reject", reason="Not justified"
    )
    from modules.psm.selectors.scoping import indents_for

    visible_indent = indents_for(da).get(pk=obj.pk)
    assert visible_indent.transitions.filter(to_status="rejected", reason="Not justified").exists()


def _case010():
    emp, da, _, ps, *_ = _ctx()
    item, _ = _stock(ps)
    obj = _indent(emp, item=item, qty=4)
    routed, reservation = stock.check_and_reserve(actor=da, indent_id=obj.pk)
    assert (
        routed.status == "stock_reserved"
        and reservation.quantity == 4
        and PsmNotification.objects.filter(topic="indent.stock_available").exists()
    )


def _case011():
    emp, da, _, ps, *_ = _ctx()
    item, _ = _stock(ps, qty=5)
    first = _indent(emp, item=item, qty=4)
    stock.check_and_reserve(actor=da, indent_id=first.pk)
    second = _indent(emp, item=item, qty=2)
    routed, reservation = stock.check_and_reserve(actor=da, indent_id=second.pk)
    assert routed.status == "external_required" and reservation is None
    assert (
        StockReservation.objects.filter(indent_id=first.pk, status="active").aggregate(
            s=Sum("quantity")
        )["s"]
        == 4
    )


def _case012():
    emp, da, _, ps, *_ = _ctx()
    item, _ = _stock(ps)
    obj = _indent(emp, item=item, qty=3)
    stock.check_and_reserve(actor=da, indent_id=obj.pk)
    approvals.dept_admin_review(actor=da, indent_id=obj.pk, decision="approve")
    issue = obj.internal_issue
    stock.schedule_picking(actor=da, issue_id=issue.pk)
    stock.dispatch_internal_issue(actor=da, issue_id=issue.pk)
    grn = receipts.record_grn(
        actor=emp, internal_issue_id=issue.pk, received_quantity=3, accepted_quantity=3
    )
    receipts.confirm_receipt(actor=emp, grn_id=grn.pk)
    assert grn.stock_posted is False
    grn.refresh_from_db()
    obj.refresh_from_db()
    assert grn.stock_posted and obj.status == "fulfilled"


def _case013():
    emp, da, _, ps, *_ = _ctx()
    item, _loc = _stock(ps)
    obj = _indent(emp, item=item, qty=3)
    stock.check_and_reserve(actor=da, indent_id=obj.pk)
    approvals.dept_admin_review(actor=da, indent_id=obj.pk, decision="approve")
    issue = obj.internal_issue
    stock.dispatch_internal_issue(actor=da, issue_id=issue.pk)
    grn = receipts.record_grn(
        actor=emp, internal_issue_id=issue.pk, received_quantity=3, accepted_quantity=3
    )
    assert not StockLedgerEntry.objects.filter(item=item, entry_type="internal_issue_post").exists()
    assert grn.stock_posted is False


def _case014():
    emp, da, hod, ps, *_ = _ctx()
    _indent_obj, _vendor_obj, po = _po(emp, da, hod, ps)
    grn = receipts.record_grn(
        actor=emp,
        purchase_order_id=po.pk,
        received_quantity=2,
        accepted_quantity=1,
        rejected_quantity=1,
    )
    case = discrepancies.report_discrepancy(
        actor=emp,
        grn_id=grn.pk,
        discrepancy_type="damage",
        affected_quantity=1,
        description="Broken",
        requested_resolution="return",
    )
    with pytest.raises(ConflictError) as refused:
        receipts.confirm_receipt(actor=emp, grn_id=grn.pk)
    assert refused.value.status_code == 409
    grn.refresh_from_db()
    assert case.status == "open" and not grn.stock_posted


def _case015():
    emp, da, hod, ps, *_ = _ctx()
    obj = _external_ready(emp, da, hod, ps)
    obj.refresh_from_db()
    assert obj.status == "procurement_authorized" and obj.procurement_method == "direct"


def _case016():
    from datetime import timedelta as td

    from modules.psm.services.approvals import sweep_slas

    emp, da, _, ps, *_ = _ctx()
    obj = _indent(emp, cost="40000.00")
    stock.check_and_reserve(actor=da, indent_id=obj.pk)
    approvals.dept_admin_review(actor=da, indent_id=obj.pk, decision="approve", priority="high")
    obj.refresh_from_db()
    assert obj.priority == "high"
    routed = procurement.review_and_select_method(actor=ps, indent_id=obj.pk)
    assert routed.status == "procurement_authorized" and routed.procurement_method == "direct"
    waiting = _indent(emp, desc="High priority queue", cost="40000.00")
    stock.check_and_reserve(actor=da, indent_id=waiting.pk)
    approvals.dept_admin_review(actor=da, indent_id=waiting.pk, decision="approve", priority="high")
    waiting.refresh_from_db()
    Indent.objects.filter(pk=waiting.pk).update(current_stage_since=timezone.now() - td(hours=13))
    sweep_slas()
    assert PsmNotification.objects.filter(
        topic="indent.reviewed", payload__indent_id=obj.pk
    ).exists()
    assert PsmNotification.objects.filter(
        topic="indent.sla_reminder", payload__indent_id=waiting.pk
    ).exists()


def _case017():
    emp, da, *_ = _ctx()
    obj = _indent(emp)
    before = obj.status
    with pytest.raises(DomainError) as refused:
        approvals.dept_admin_review(actor=da, indent_id=obj.pk, decision="reject", reason="")
    assert refused.value.status_code == 422
    obj.refresh_from_db()
    assert (
        obj.status == before
        and not PsmAuditLog.objects.filter(target_id=obj.pk, action__contains="reject").exists()
    )


def _case018():
    emp, da, *_ = _ctx()
    obj = _indent(emp)
    stock.check_and_reserve(actor=da, indent_id=obj.pk)
    approvals.dept_admin_review(
        actor=da, indent_id=obj.pk, decision="reject", reason="Budget mismatch"
    )
    obj.refresh_from_db()
    assert obj.status == "rejected" and obj.rejection_reason == "Budget mismatch"
    assert PsmAuditLog.objects.filter(
        target_type="indent", target_id=obj.pk, action__contains="reject"
    ).exists()


def _case019():
    from datetime import timedelta

    from django.utils import timezone as tz

    from modules.psm.services.approvals import sweep_slas

    emp, *_ = _ctx()
    obj = _indent(emp)
    Indent.objects.filter(pk=obj.pk).update(current_stage_since=tz.now() - timedelta(hours=25))
    reminder = sweep_slas(now=tz.now())
    Indent.objects.filter(pk=obj.pk).update(current_stage_since=tz.now() - timedelta(days=3))
    escalation = sweep_slas(now=tz.now())
    assert reminder["reminded"] == 1 and escalation["escalated"] == 1
    assert PsmNotification.objects.filter(
        topic="indent.sla_reminder", payload__indent_id=obj.pk
    ).exists()
    assert PsmNotification.objects.filter(
        topic="indent.sla_escalation", payload__indent_id=obj.pk
    ).exists()


def _case020():
    emp, da, *_ = _ctx()
    obj = _indent(emp)
    routed, reservation = stock.check_and_reserve(actor=da, indent_id=obj.pk)
    assert routed.status == "external_required" and reservation is None


def _case021():
    emp, da, hod, ps, *_ = _ctx()
    direct = _external_ready(emp, da, hod, ps, cost="40000.00", desc="Direct threshold")
    direct.refresh_from_db()
    assert direct.procurement_method == "direct"


def _case022():
    emp, da, hod, ps, *_ = _ctx()
    obj = _external_ready(emp, da, hod, ps, cost="250000.00", desc="Tender item")
    approvals.final_decision(actor=_actor(11005, "Director"), indent_id=obj.pk, decision="approve")
    t = tenders.create_tender(
        actor=ps,
        indent_id=obj.pk,
        title="Tender",
        scope="Supply",
        evaluation_criteria="Quality and price",
        submission_deadline=timezone.now() + timedelta(days=10),
    )
    tenders.publish_tender(actor=ps, tender_id=t.pk)
    v = _vendor(ps)
    bid = tenders.record_bid(
        actor=ps, tender_id=t.pk, vendor_id=v.pk, quoted_amount=Decimal("240000")
    )
    tenders.evaluate_bids(
        actor=ps,
        tender_id=t.pk,
        evaluations=[{"bid_id": bid.pk, "technical_score": 90, "financial_score": 95}],
        committee_members=["Chair"],
        committee_minutes="Approved",
    )
    awarded = tenders.award_tender(actor=ps, tender_id=t.pk, bid_id=bid.pk)
    assert (
        awarded.awarded_vendor_id == v.pk
        and awarded.committee_minutes
        and TenderBid.objects.filter(pk=bid.pk, is_selected=True).exists()
    )


def _case023():
    emp, da, hod, ps, *_ = _ctx()
    obj, vendor, po = _po(emp, da, hod, ps)
    assert (
        po.indent_id == obj.pk
        and po.vendor_id == vendor.pk
        and po.issued_by_user_id == ps.user_id
        and vendor.is_verified
    )


def _case024():
    emp, _da, _hod, ps, *_ = _ctx()
    obj = _indent(emp)
    vendor = _vendor(ps)
    with pytest.raises(ConflictError) as refused:
        procurement.create_and_issue_po(
            actor=ps,
            indent_id=obj.pk,
            vendor_id=vendor.pk,
            unit_price=Decimal("10"),
            planned_delivery_date=date.today() + timedelta(days=1),
        )
    assert refused.value.status_code == 409
    assert not PurchaseOrder.objects.filter(indent=obj).exists()


def _case025():
    emp, da, hod, ps, *_ = _ctx()
    _, _, po = _po(emp, da, hod, ps)
    actual = date.today() + timedelta(days=11)
    changed = procurement.update_po_schedule(actor=ps, po_id=po.pk, actual_delivery_date=actual)
    assert (
        changed.planned_delivery_date == po.planned_delivery_date
        and changed.actual_delivery_date == actual
    )


def _case026():
    emp, da, hod, ps, *_ = _ctx()
    _, _, po = _po(emp, da, hod, ps, qty=4)
    grn = receipts.record_grn(
        actor=emp,
        purchase_order_id=po.pk,
        received_quantity=2,
        accepted_quantity=1,
        rejected_quantity=1,
        inspection_notes="One damaged",
    )
    assert grn.received_quantity == 2 and grn.accepted_quantity == 1 and grn.rejected_quantity == 1


def _case027():
    emp, da, hod, ps, *_ = _ctx()
    item, _loc = _stock(ps, qty=0)
    obj = _external_ready(emp, da, hod, ps)
    obj.item_id = item.pk
    obj.save(update_fields=["item"])
    vendor = _vendor(ps)
    po = procurement.create_and_issue_po(
        actor=ps,
        indent_id=obj.pk,
        vendor_id=vendor.pk,
        unit_price=Decimal("500"),
        ordered_quantity=2,
        planned_delivery_date=date.today() + timedelta(days=2),
    )
    grn = receipts.record_grn(
        actor=emp, purchase_order_id=po.pk, received_quantity=2, accepted_quantity=2
    )
    assert not StockLedgerEntry.objects.filter(item=item, entry_type="receipt_post").exists()
    assert not grn.stock_posted


def _case028():
    emp, da, hod, ps, *_ = _ctx()
    item, _loc = _stock(ps, qty=0)
    obj = _external_ready(emp, da, hod, ps)
    obj.item_id = item.pk
    obj.save(update_fields=["item"])
    vendor = _vendor(ps)
    po = procurement.create_and_issue_po(
        actor=ps,
        indent_id=obj.pk,
        vendor_id=vendor.pk,
        unit_price=Decimal("500"),
        ordered_quantity=2,
        planned_delivery_date=date.today() + timedelta(days=2),
    )
    grn = receipts.record_grn(
        actor=emp, purchase_order_id=po.pk, received_quantity=2, accepted_quantity=2
    )
    receipts.confirm_receipt(actor=emp, grn_id=grn.pk)
    assert StockLedgerEntry.objects.filter(
        item=item, source_ref_id=grn.pk, entry_type="receipt_post", quantity_delta=2
    ).exists()


def _case029():
    emp, da, hod, ps, *_ = _ctx()
    _, _, po = _po(emp, da, hod, ps)
    grn = receipts.record_grn(
        actor=emp,
        purchase_order_id=po.pk,
        received_quantity=2,
        accepted_quantity=1,
        rejected_quantity=1,
    )
    c = discrepancies.report_discrepancy(
        actor=emp,
        grn_id=grn.pk,
        discrepancy_type="damage",
        affected_quantity=1,
        description="Broken",
        requested_resolution="replacement",
        evidence_url="https://drive.google.com/file/d/1AbCdEfGhIjKlMnOpQrStUvWx/view",
        evidence_filename="damage.jpg",
    )
    assert c.grn_id == grn.pk and c.evidence_url and c.evidence_filename == "damage.jpg"


def _case030():
    emp, da, hod, ps, *_ = _ctx()
    _, _, po = _po(emp, da, hod, ps)
    grn = receipts.record_grn(
        actor=emp,
        purchase_order_id=po.pk,
        received_quantity=2,
        accepted_quantity=1,
        rejected_quantity=1,
    )
    c = discrepancies.report_discrepancy(
        actor=emp,
        grn_id=grn.pk,
        discrepancy_type="damage",
        affected_quantity=1,
        description="Broken",
        requested_resolution="return",
    )
    done = discrepancies.resolve_case(
        actor=ps, case_id=c.pk, resolution_action="resolve", resolution_notes="Returned to vendor"
    )
    assert done.status == "resolved" and done.resolution_notes == "Returned to vendor"


def _case031():
    emp, da, hod, ps, *_ = _ctx()
    _, _, po = _po(emp, da, hod, ps)
    grn = receipts.record_grn(
        actor=emp,
        purchase_order_id=po.pk,
        received_quantity=2,
        accepted_quantity=1,
        rejected_quantity=1,
    )
    c = discrepancies.report_discrepancy(
        actor=emp,
        grn_id=grn.pk,
        discrepancy_type="damage",
        affected_quantity=1,
        description="Broken",
        requested_resolution="replacement",
    )
    comm = discrepancies.add_communication(
        actor=ps, case_id=c.pk, sender_label="Vendor", message="Replacement arranged"
    )
    changed = discrepancies.resolve_case(
        actor=ps, case_id=c.pk, resolution_action="resolve", resolution_notes="Replaced"
    )
    assert (
        DiscrepancyCommunication.objects.filter(pk=comm.pk, case=c).exists()
        and changed.status == "resolved"
        and changed.resolution_notes == "Replaced"
    )


def _case032():
    emp, da, hod, ps, *_ = _ctx()
    item, _loc = _stock(ps, qty=5)
    indent = _external_ready(emp, da, hod, ps, desc="Disputed stock", qty=2)
    indent.item = item
    indent.save(update_fields=["item"])
    vendor = _vendor(ps)
    po = procurement.create_and_issue_po(
        actor=ps,
        indent_id=indent.pk,
        vendor_id=vendor.pk,
        unit_price=Decimal("20000"),
        planned_delivery_date=date.today() + timedelta(days=3),
    )
    grn = receipts.record_grn(
        actor=emp,
        purchase_order_id=po.pk,
        received_quantity=2,
        accepted_quantity=1,
        rejected_quantity=1,
    )
    receipts.confirm_receipt(actor=emp, grn_id=grn.pk)
    c = discrepancies.report_discrepancy(
        actor=emp,
        grn_id=grn.pk,
        discrepancy_type="damage",
        affected_quantity=1,
        description="Broken",
        requested_resolution="return",
    )
    invoice = finance.submit_invoice(
        actor=_actor(11006, "Accounts Admin"),
        purchase_order_id=po.pk,
        invoice_number="FR-DISC-ADJUST",
        billed_quantity=2,
        billed_amount=po.total_amount,
    )
    finance.verify_invoice(actor=_actor(11006, "Accounts Admin"), invoice_id=invoice.pk)
    discrepancies.resolve_case(
        actor=ps,
        case_id=c.pk,
        resolution_action="resolve",
        resolution_notes="Adjust",
        inventory_adjusted=True,
        accounting_adjusted=True,
    )
    assert (
        StockLedgerEntry.objects.filter(source_ref_type="discrepancy", source_ref_id=c.pk).exists()
        and PsmAuditLog.objects.filter(
            target_type="invoice", target_id=invoice.pk, action="invoice.discrepancy_adjusted"
        ).exists()
    )


def _case033():
    emp, da, hod, ps, acc, *_ = _ctx()
    _, _, po = _po(emp, da, hod, ps)
    grn = receipts.record_grn(
        actor=emp, purchase_order_id=po.pk, received_quantity=2, accepted_quantity=2
    )
    receipts.confirm_receipt(actor=emp, grn_id=grn.pk)
    inv = finance.submit_invoice(
        actor=acc,
        purchase_order_id=po.pk,
        invoice_number="FR-MATCH",
        billed_quantity=2,
        billed_amount=po.total_amount,
    )
    verified = finance.verify_invoice(actor=acc, invoice_id=inv.pk)
    assert verified.status == "verified" and verified.eligible_amount == po.total_amount


def _case034():
    emp, da, hod, ps, acc, *_ = _ctx()
    _, _vendor_obj, po = _po(emp, da, hod, ps)
    inv = finance.submit_invoice(
        actor=acc,
        purchase_order_id=po.pk,
        invoice_number="FR-PREPAY",
        billed_quantity=2,
        billed_amount=po.total_amount,
    )
    with pytest.raises(ConflictError) as refused:
        finance.process_payment(
            actor=acc, invoice_id=inv.pk, amount=Decimal("100"), payment_reference="FR-BLOCK"
        )
    assert refused.value.status_code == 409
    assert not PaymentTransaction.objects.filter(invoice=inv).exists()


def _case035():
    emp, da, hod, ps, acc, *_ = _ctx()
    _, _, po = _po(emp, da, hod, ps)
    grn = receipts.record_grn(
        actor=emp, purchase_order_id=po.pk, received_quantity=2, accepted_quantity=2
    )
    receipts.confirm_receipt(actor=emp, grn_id=grn.pk)
    inv = finance.submit_invoice(
        actor=acc,
        purchase_order_id=po.pk,
        invoice_number="FR-PAID",
        billed_quantity=2,
        billed_amount=po.total_amount,
    )
    finance.verify_invoice(actor=acc, invoice_id=inv.pk)
    tx = finance.process_payment(
        actor=acc, invoice_id=inv.pk, amount=po.total_amount, payment_reference="FR-PAID-REF"
    )
    inv.refresh_from_db()
    assert tx.status == "released" and inv.status == "paid"


def _case036():
    emp, da, hod, ps, acc, *_ = _ctx()
    _, _, po = _po(emp, da, hod, ps)
    inv = finance.submit_invoice(
        actor=acc,
        purchase_order_id=po.pk,
        invoice_number="FR-MISMATCH",
        billed_quantity=9,
        billed_amount=Decimal("90000"),
    )
    held = finance.verify_invoice(actor=acc, invoice_id=inv.pk)
    assert held.status == "on_hold" and held.eligible_amount == 0


def _case037():
    emp, da, hod, ps, acc, *_ = _ctx()
    _, _, po = _po(emp, da, hod, ps)
    grn = receipts.record_grn(
        actor=emp, purchase_order_id=po.pk, received_quantity=2, accepted_quantity=2
    )
    receipts.confirm_receipt(actor=emp, grn_id=grn.pk)
    inv = finance.submit_invoice(
        actor=acc,
        purchase_order_id=po.pk,
        invoice_number="FR-PART",
        billed_quantity=2,
        billed_amount=po.total_amount,
    )
    finance.verify_invoice(actor=acc, invoice_id=inv.pk)
    inv.refresh_from_db()
    eligible_amount = inv.eligible_amount
    eligible_amount = inv.eligible_amount
    tx = finance.process_payment(
        actor=acc, invoice_id=inv.pk, amount=po.total_amount / 2, payment_reference="FR-PART-REF"
    )
    assert tx.is_partial and tx.amount < eligible_amount


def _case038():
    *_, ps, _, _, _ = _ctx()
    v = _vendor(ps)
    changed = vendors.update_vendor(
        actor=ps,
        vendor_id=v.pk,
        contact_email="updated@example.test",
        change_reason="Contact update",
    )
    assert (
        changed.version == 3
        and VendorVersion.objects.filter(vendor=v).count() == 3
        and PsmAuditLog.objects.filter(
            target_type="vendor", target_id=v.pk, action="vendor.updated"
        ).exists()
    )


def _case039():
    *_, ps, _, _, _ = _ctx()
    v = vendors.onboard_vendor(
        actor=ps,
        name="Bad Vendor",
        gstin="bad",
        bank_account_number="x",
        bank_ifsc="bad",
        bank_name="",
        compliance_documents=[],
    )
    with pytest.raises(DomainError):
        vendors.verify_vendor(actor=ps, vendor_id=v.pk)
    v.refresh_from_db()
    assert not v.is_verified


def _case040():
    emp, da, hod, ps, _acc, *_ = _ctx()
    obj = _external_ready(emp, da, hod, ps)
    vendor = _vendor(ps, verified=False)
    with pytest.raises(ConflictError) as po_refused:
        procurement.create_and_issue_po(
            actor=ps,
            indent_id=obj.pk,
            vendor_id=vendor.pk,
            unit_price=Decimal("10"),
            planned_delivery_date=date.today() + timedelta(days=1),
        )
    assert po_refused.value.status_code == 409
    assert not PurchaseOrder.objects.filter(indent=obj).exists()
    po = PurchaseOrder.objects.create(
        po_number="FR-UNVERIFIED-PO",
        indent=obj,
        vendor=vendor,
        ordered_quantity=obj.quantity,
        unit_price=Decimal("20000"),
        total_amount=Decimal("40000"),
        status="delivered",
        planned_delivery_date=date.today(),
        issued_by_user_id=ps.user_id,
    )
    acc = _actor(11006, "Accounts Admin")
    invoice = finance.submit_invoice(
        actor=acc,
        purchase_order_id=po.pk,
        invoice_number="FR-UNVERIFIED-INV",
        billed_quantity=obj.quantity,
        billed_amount=po.total_amount,
    )
    invoice.status = "verified"
    invoice.eligible_amount = po.total_amount
    invoice.save(update_fields=["status", "eligible_amount"])
    with pytest.raises(ConflictError) as pay_refused:
        finance.process_payment(
            actor=acc,
            invoice_id=invoice.pk,
            amount=po.total_amount,
            payment_reference="FR-UNVERIFIED-PAY",
        )
    assert pay_refused.value.status_code == 409
    assert not PaymentTransaction.objects.filter(invoice=invoice).exists()


def _case041():
    _emp, da, _hod, ps, *_ = _ctx()
    item, src = _stock(ps, qty=10)
    dst = stock.create_stock_location(actor=ps, code="FR-DST", name="ECE", department="ECE")
    destination_admin = _actor(11008, "deptadmin_ece")
    tr = transfers.request_transfer(
        actor=destination_admin,
        item_id=item.pk,
        source_location_id=src.pk,
        destination_location_id=dst.pk,
        quantity=3,
    )
    transfers.dispatch_transfer(actor=da, transfer_id=tr.pk)
    completed = transfers.confirm_transfer(actor=destination_admin, transfer_id=tr.pk)
    assert (
        completed.status == "completed"
        and StockLedgerEntry.objects.filter(
            source_ref_type="stock_transfer", source_ref_id=tr.pk
        ).count()
        == 2
        and PsmAuditLog.objects.filter(target_type="stock_transfer", target_id=tr.pk).exists()
    )


def _case042():
    *_, aud = _ctx()
    results = [
        reports.generate_report(actor=aud, report_type=kind)
        for kind in ("operational", "procurement", "stock", "financial")
    ]
    assert {r["report_type"] for r in results} == {
        "operational",
        "procurement",
        "stock",
        "financial",
    }


def _case043():
    *_, _ps, _, _, aud = _ctx()
    reports.generate_report(actor=aud, report_type="stock", filters={"department": "CSE"})
    name, csv_body = reports.export_report_csv(
        actor=aud, report_type="stock", filters={"department": "CSE"}
    )
    sched = reports.create_schedule(
        actor=aud,
        name="Weekly",
        report_type="stock",
        cadence="weekly",
        filters={"department": "CSE"},
    )
    assert (
        name.endswith(".csv")
        and csv_body
        and sched.is_active
        and ReportGenerationLog.objects.filter(report_type="stock").count() == 2
    )


def _case044():
    from modules.psm.selectors.dashboard import dashboard_summary

    *_, aud = _ctx()
    _indent(_actor(11101, "faculty"))
    data = dashboard_summary(aud)
    assert isinstance(data, dict) and data


def _case045():
    emp, da, *_ = _ctx()
    obj = _indent(emp)
    stock.check_and_reserve(actor=da, indent_id=obj.pk)
    approvals.dept_admin_review(actor=da, indent_id=obj.pk, decision="approve")
    assert (
        PsmNotification.objects.filter(topic="indent.submitted", payload__indent_id=obj.pk).exists()
        and PsmNotification.objects.filter(
            topic="indent.reviewed", payload__indent_id=obj.pk
        ).exists()
    )


def _case046():
    emp, da, hod, ps, acc, *_ = _ctx()
    _, _, po = _po(emp, da, hod, ps)
    procurement.update_po_schedule(actor=ps, po_id=po.pk, status="in_transit")
    grn = receipts.record_grn(
        actor=emp, purchase_order_id=po.pk, received_quantity=2, accepted_quantity=2
    )
    receipts.confirm_receipt(actor=emp, grn_id=grn.pk)
    inv = finance.submit_invoice(
        actor=acc,
        purchase_order_id=po.pk,
        invoice_number="FR-EVENTS",
        billed_quantity=2,
        billed_amount=po.total_amount,
    )
    finance.verify_invoice(actor=acc, invoice_id=inv.pk)
    finance.process_payment(
        actor=acc, invoice_id=inv.pk, amount=po.total_amount, payment_reference="FR-EVENT-PAY"
    )
    topics = set(PsmNotification.objects.values_list("topic", flat=True))
    assert {
        "po.status_changed",
        "grn.recorded",
        "grn.confirmed",
        "invoice.verified",
        "payment.released",
    }.issubset(topics)


def _case047():
    from datetime import timedelta

    from modules.psm.services.approvals import sweep_slas

    emp, *_ = _ctx()
    obj = _indent(emp)
    Indent.objects.filter(pk=obj.pk).update(
        current_stage_since=timezone.now() - timedelta(hours=25)
    )
    sweep_slas()
    Indent.objects.filter(pk=obj.pk).update(current_stage_since=timezone.now() - timedelta(days=3))
    sweep_slas()
    assert PsmNotification.objects.filter(topic="indent.sla_reminder").exists()
    assert PsmNotification.objects.filter(topic="indent.sla_escalation").exists()
    assert PsmNotification.objects.count() >= 2


def _case048():
    emp, *_ = _ctx()
    obj = _indent(emp)
    assert PsmAuditLog.objects.filter(
        target_type="indent", target_id=obj.pk, action="indent.submitted"
    ).exists()


def _case049():
    emp, da, _hod, _ps, _, _, aud = _ctx()
    obj = _indent(emp)
    stock.check_and_reserve(actor=da, indent_id=obj.pk)
    approvals.dept_admin_review(actor=da, indent_id=obj.pk, decision="approve")
    from modules.psm.selectors.scoping import audit_logs_for

    accessible = list(
        audit_logs_for(aud)
        .filter(target_type="indent", target_id=obj.pk)
        .values_list("action", flat=True)
    )
    assert "indent.submitted" in accessible and "indent.department_reviewed" in accessible


def _case050(request):
    from rest_framework.test import APIClient

    from conftest import make_session

    emp, *_ = _ctx()
    obj = _indent(emp)
    install = request.getfixturevalue("stub_iam")
    install(
        make_session(
            user_id=emp.user_id,
            kind="faculty",
            active_role="faculty",
            roles=("faculty",),
            modules=("psm",),
            permissions=tuple(registry.ROLE_GRANTS["faculty"]),
        )
    )
    authorized = APIClient()
    authorized.credentials(HTTP_AUTHORIZATION="Token authorized")
    assert authorized.get(f"/api/v1/psm/indents/{obj.pk}").status_code == 200
    install(
        make_session(
            user_id=11999,
            kind="staff",
            active_role="staff",
            roles=("staff",),
            modules=("psm",),
            permissions=(),
        )
    )
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token unauthorized")
    response = client.patch(f"/api/v1/psm/indents/{obj.pk}", {"quantity": 9}, format="json")
    assert response.status_code == 403
    obj.refresh_from_db()
    assert obj.quantity == 2


def _case051():
    from modules.psm.models import PsmPolicy

    emp, da, hod, ps, *_ = _ctx()
    PsmPolicy.objects.filter(is_active=True).update(direct_limit=Decimal("10000.00"))
    obj = _external_ready(emp, da, hod, ps, cost="40000.00")
    obj.refresh_from_db()
    assert PsmPolicy.objects.get(is_active=True).direct_limit == Decimal("10000.00")
    assert obj.procurement_method == "tender"


def _case052():
    from modules.psm.models import PsmPolicy

    emp, da, hod, ps, _, acc, *_ = _ctx()
    _, _, po = _po(emp, da, hod, ps)
    grn = receipts.record_grn(
        actor=emp, purchase_order_id=po.pk, received_quantity=2, accepted_quantity=2
    )
    receipts.confirm_receipt(actor=emp, grn_id=grn.pk)
    inv = finance.submit_invoice(
        actor=acc,
        purchase_order_id=po.pk,
        invoice_number="FR-NOPART",
        billed_quantity=2,
        billed_amount=po.total_amount,
    )
    finance.verify_invoice(actor=acc, invoice_id=inv.pk)
    PsmPolicy.objects.filter(is_active=True).update(partial_payment_enabled=False)
    with pytest.raises(ConflictError) as refused:
        finance.process_payment(
            actor=acc,
            invoice_id=inv.pk,
            amount=po.total_amount / 2,
            payment_reference="FR-NOPART-REF",
        )
    assert refused.value.status_code == 409
    assert not PaymentTransaction.objects.filter(invoice=inv).exists()


_CASES = {
    "PSM-001": _case001,
    "PSM-002": _case002,
    "PSM-003": _case003,
    "PSM-004": _case004,
    "PSM-005": _case005,
    "PSM-006": _case006,
    "PSM-007": _case007,
    "PSM-008": _case008,
    "PSM-009": _case009,
    "PSM-010": _case010,
    "PSM-011": _case011,
    "PSM-012": _case012,
    "PSM-013": _case013,
    "PSM-014": _case014,
    "PSM-015": _case015,
    "PSM-016": _case016,
    "PSM-017": _case017,
    "PSM-018": _case018,
    "PSM-019": _case019,
    "PSM-020": _case020,
    "PSM-021": _case021,
    "PSM-022": _case022,
    "PSM-023": _case023,
    "PSM-024": _case024,
    "PSM-025": _case025,
    "PSM-026": _case026,
    "PSM-027": _case027,
    "PSM-028": _case028,
    "PSM-029": _case029,
    "PSM-030": _case030,
    "PSM-031": _case031,
    "PSM-032": _case032,
    "PSM-033": _case033,
    "PSM-034": _case034,
    "PSM-035": _case035,
    "PSM-036": _case036,
    "PSM-037": _case037,
    "PSM-038": _case038,
    "PSM-039": _case039,
    "PSM-040": _case040,
    "PSM-041": _case041,
    "PSM-042": _case042,
    "PSM-043": _case043,
    "PSM-044": _case044,
    "PSM-045": _case045,
    "PSM-046": _case046,
    "PSM-047": _case047,
    "PSM-048": _case048,
    "PSM-049": _case049,
    "PSM-050": _case050,
    "PSM-051": _case051,
    "PSM-052": _case052,
}
_DESIGN = json.loads(
    (Path(__file__).resolve().parents[5] / "docs/09-psm/spec-tests/FR_DESIGN.json").read_text(
        encoding="utf-8"
    )
)
assert len(_DESIGN) == len(_CASES) == 52


def _build_test(case):
    case_id, sources = case["test_id"], case["source_id"]
    handler = _CASES[case_id]

    def test_case(request):
        if case_id == "PSM-050":
            handler(request)
        else:
            handler()

    test_case.__name__ = "test_" + case_id.lower().replace("-", "_")
    test_case.__doc__ = f"{case_id}; source_id: {sources}. {case['purpose']}"
    return test_case


for _case in _DESIGN:
    globals()["test_" + _case["test_id"].lower().replace("-", "_")] = _build_test(_case)
