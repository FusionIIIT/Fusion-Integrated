# Invoice submission, three-way matching, holds, and append-only payment release (PSM-UC-013, 029).
from __future__ import annotations

from decimal import Decimal

from django.db import IntegrityError, transaction
from django.db.models import Sum
from django.utils import timezone

from core.api.exceptions import ConflictError, DomainError, NotFoundError
from modules.psm.domain import finance_rules as fr
from modules.psm.domain import state_machine as sm
from modules.psm.models import (
    DiscrepancyCase,
    GoodsReceiptNote,
    Invoice,
    PaymentTransaction,
    PurchaseOrder,
)
from modules.psm.services.common import (
    audit_record,
    enqueue_notification,
    next_number,
    policy_to_spec,
    require_active_policy,
    translate_errors,
)


@transaction.atomic
def submit_invoice(
    *,
    actor,
    purchase_order_id: int,
    invoice_number: str,
    billed_quantity: int,
    billed_amount: Decimal,
) -> Invoice:
    """Record a vendor invoice linked to a purchase order (PSM-UC-013)."""
    po = (
        PurchaseOrder.objects.select_related("vendor", "indent")
        .filter(pk=purchase_order_id)
        .first()
    )
    if po is None:
        raise NotFoundError("Purchase order not found.")
    if billed_quantity <= 0 or billed_amount <= Decimal("0"):
        raise DomainError(
            "Billed quantity and billed amount must be greater than zero.",
            code="invalid_invoice_amounts",
        )
    try:
        invoice = Invoice.objects.create(
            invoice_number=invoice_number.strip(),
            purchase_order=po,
            vendor=po.vendor,
            billed_quantity=billed_quantity,
            billed_amount=billed_amount,
            status=sm.INV_SUBMITTED,
            submitted_by_user_id=actor.user_id,
        )
    except IntegrityError as exc:
        raise ConflictError(
            "An invoice with that number already exists for this vendor.", code="duplicate_invoice"
        ) from exc
    audit_record(
        actor=actor,
        action="invoice.submitted",
        target_type="invoice",
        target_id=invoice.pk,
        to_state=sm.INV_SUBMITTED,
    )
    return invoice


@transaction.atomic
def verify_invoice(*, actor, invoice_id: int) -> Invoice:
    """Perform three-way PO-GRN-Invoice match (PSM-UC-013, BR-PSM-017, 018)."""
    policy = require_active_policy()
    spec = policy_to_spec(policy)
    invoice = (
        Invoice.objects.select_for_update()
        .select_related("purchase_order", "purchase_order__indent", "vendor")
        .filter(pk=invoice_id)
        .first()
    )
    if invoice is None:
        raise NotFoundError("Invoice not found.")
    if invoice.status in (sm.INV_PAID, sm.INV_PARTIALLY_PAID):
        raise ConflictError(
            f"Cannot re-verify an invoice that is already '{invoice.status}'.",
            code="invoice_already_paid",
        )
    po = invoice.purchase_order
    confirmed_qty = (
        GoodsReceiptNote.objects.filter(purchase_order=po, status="confirmed").aggregate(
            t=Sum("accepted_quantity")
        )["t"]
        or 0
    )
    has_open_disc = (
        DiscrepancyCase.objects.filter(grn__purchase_order=po)
        .exclude(status__in=(sm.DISC_RESOLVED, sm.DISC_CLOSED))
        .exists()
    )
    outcome = fr.three_way_match(
        fr.ThreeWayMatchInput(
            po_ordered_quantity=po.ordered_quantity,
            po_unit_price=po.unit_price,
            po_total_amount=po.total_amount,
            confirmed_accepted_quantity=confirmed_qty,
            billed_quantity=invoice.billed_quantity,
            billed_amount=invoice.billed_amount,
            has_open_discrepancy=has_open_disc,
            vendor_verified=invoice.vendor.is_verified and invoice.vendor.is_active,
            partial_payment_enabled=spec.partial_payment_enabled,
        )
    )
    old_status = invoice.status
    if outcome.matched:
        with translate_errors():
            sm.resolve("invoice", invoice.status, sm.INV_VERIFIED, sm.ACCOUNTS)
        invoice.status = sm.INV_VERIFIED
        invoice.eligible_amount = outcome.eligible_amount
        invoice.hold_reason = ""
        invoice.verified_by_user_id = actor.user_id
        invoice.verified_at = timezone.now()
    else:
        with translate_errors():
            sm.resolve("invoice", invoice.status, sm.INV_ON_HOLD, sm.ACCOUNTS)
        invoice.status = sm.INV_ON_HOLD
        invoice.eligible_amount = Decimal("0.00")
        invoice.hold_reason = outcome.hold_reason
    invoice.save(
        update_fields=[
            "status",
            "eligible_amount",
            "hold_reason",
            "verified_by_user_id",
            "verified_at",
            "updated_at",
        ]
    )
    audit_record(
        actor=actor,
        action="invoice.verified" if outcome.matched else "invoice.held",
        target_type="invoice",
        target_id=invoice.pk,
        from_state=old_status,
        to_state=invoice.status,
        details={"hold_reason": invoice.hold_reason} if invoice.hold_reason else {},
    )
    enqueue_notification(
        topic=f"invoice.{invoice.status}",
        dedupe_key=f"invoice.verify:{invoice.pk}:{invoice.status}:{invoice.updated_at.isoformat()}",
        recipient_user_id=po.indent.user_id,
        subject=f"Invoice {invoice.invoice_number} is now {invoice.status}",
        body=invoice.hold_reason or f"Invoice verified for {invoice.eligible_amount}.",
        payload={"invoice_id": invoice.pk, "status": invoice.status},
    )
    return invoice


@transaction.atomic
def hold_invoice(*, actor, invoice_id: int, reason: str) -> Invoice:
    """Explicitly place an invoice on hold with a mandatory reason (PSM-UC-029, BR-PSM-018)."""
    cleaned = (reason or "").strip()
    if not cleaned:
        raise DomainError(
            "Provide a reason before placing this invoice on hold.", code="hold_reason_required"
        )
    invoice = (
        Invoice.objects.select_for_update()
        .select_related("purchase_order__indent")
        .filter(pk=invoice_id)
        .first()
    )
    if invoice is None:
        raise NotFoundError("Invoice not found.")
    with translate_errors():
        sm.resolve("invoice", invoice.status, sm.INV_ON_HOLD, sm.ACCOUNTS)
    old_status = invoice.status
    invoice.status = sm.INV_ON_HOLD
    invoice.hold_reason = cleaned
    invoice.save(update_fields=["status", "hold_reason", "updated_at"])
    audit_record(
        actor=actor,
        action="invoice.held",
        target_type="invoice",
        target_id=invoice.pk,
        from_state=old_status,
        to_state=sm.INV_ON_HOLD,
        details={"reason": cleaned},
    )
    return invoice


@transaction.atomic
def process_payment(
    *, actor, invoice_id: int, amount: Decimal, payment_reference: str = "", notes: str = ""
) -> PaymentTransaction:
    """Release eligible full or partial payment (PSM-UC-029, BR-PSM-017, 022)."""
    policy = require_active_policy()
    spec = policy_to_spec(policy)
    invoice = (
        Invoice.objects.select_for_update()
        .select_related("purchase_order", "purchase_order__indent", "vendor")
        .filter(pk=invoice_id)
        .first()
    )
    if invoice is None:
        raise NotFoundError("Invoice not found.")
    already_paid = PaymentTransaction.objects.filter(invoice=invoice, status="released").aggregate(
        t=Sum("amount")
    )["t"] or Decimal("0.00")
    has_open_disc = (
        DiscrepancyCase.objects.filter(grn__purchase_order=invoice.purchase_order)
        .exclude(status__in=(sm.DISC_RESOLVED, sm.DISC_CLOSED))
        .exists()
    )
    with translate_errors():
        is_partial = fr.validate_payment_release(
            invoice_status=invoice.status,
            eligible_amount=invoice.eligible_amount,
            already_paid=already_paid,
            requested_amount=amount,
            vendor_verified=invoice.vendor.is_verified and invoice.vendor.is_active,
            has_open_discrepancy=has_open_disc,
            partial_payment_enabled=spec.partial_payment_enabled,
        )
    target_status = sm.INV_PARTIALLY_PAID if is_partial else sm.INV_PAID
    with translate_errors():
        sm.resolve("invoice", invoice.status, target_status, sm.ACCOUNTS)
    ref = (payment_reference or next_number("PAY")).strip()
    try:
        tx = PaymentTransaction.objects.create(
            invoice=invoice,
            vendor=invoice.vendor,
            amount=amount,
            payment_reference=ref,
            is_partial=is_partial,
            status="released",
            processed_by_user_id=actor.user_id,
            notes=notes.strip(),
        )
    except IntegrityError as exc:
        raise ConflictError(
            "That payment reference has already been used.", code="duplicate_payment_reference"
        ) from exc
    old_status = invoice.status
    invoice.status = target_status
    invoice.save(update_fields=["status", "updated_at"])
    audit_record(
        actor=actor,
        action="payment.released",
        target_type="invoice",
        target_id=invoice.pk,
        from_state=old_status,
        to_state=target_status,
        details={"payment_id": tx.pk, "amount": str(amount)},
    )
    enqueue_notification(
        topic="payment.released",
        dedupe_key=f"payment.released:{tx.pk}",
        recipient_user_id=invoice.purchase_order.indent.user_id,
        subject=f"Payment {tx.payment_reference} released for {invoice.invoice_number}",
        body=f"Released {amount} ({'partial' if is_partial else 'full'}) to {invoice.vendor.name}.",
        payload={"payment_id": tx.pk, "invoice_id": invoice.pk},
    )
    return tx
