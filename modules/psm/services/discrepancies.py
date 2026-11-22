# Discrepancy reporting, vendor comms, and resolution (PSM-UC-020, 032).
from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, DomainError, NotFoundError
from core.files.drive import InvalidDriveLink
from core.files.drive import parse as parse_drive_link
from core.files.validators import sanitise_filename
from modules.psm.domain import state_machine as sm
from modules.psm.models import (
    DiscrepancyCase,
    DiscrepancyCommunication,
    Invoice,
    StockItem,
    StockLedgerEntry,
    StockLocation,
)
from modules.psm.selectors import scoping
from modules.psm.services.common import (
    audit_record,
    enqueue_notification,
    next_number,
    translate_errors,
)


def _clean_evidence(evidence_url: str, evidence_filename: str) -> tuple[str, str]:
    """Validate optional Google Drive evidence URL and sanitize filename (AFR-PSM-049)."""
    clean_url = ""
    if (evidence_url or "").strip():
        try:
            clean_url = parse_drive_link(evidence_url).url
        except InvalidDriveLink as exc:
            raise DomainError(exc.message, code=exc.code) from exc
    clean_name = (
        sanitise_filename(evidence_filename, fallback="evidence") if evidence_filename else ""
    )
    return clean_url, clean_name


def _hold_po_invoices(purchase_order_id: int | None, case_number: str) -> None:
    """Place open PO invoices on hold when a discrepancy case is opened (BR-PSM-018)."""
    if not purchase_order_id:
        return
    Invoice.objects.filter(
        purchase_order_id=purchase_order_id,
        status__in=(sm.INV_SUBMITTED, sm.INV_VERIFIED),
    ).update(
        status=sm.INV_ON_HOLD,
        hold_reason=f"Blocked by open discrepancy case {case_number}",
    )


def _apply_inventory_adjustment(actor, case: DiscrepancyCase, notes: str) -> None:
    """Post an atomic StockLedgerEntry adjustment for a resolved discrepancy (AFR-PSM-054)."""
    grn = case.grn
    indent = grn.purchase_order.indent if grn.purchase_order_id else grn.internal_issue.indent
    if not indent.item_id:
        return
    loc = (
        StockLocation.objects.filter(department__iexact=indent.department).first()
        or StockLocation.objects.filter(is_central=True).first()
        or StockLocation.objects.first()
    )
    if loc is None:
        return
    StockItem.objects.select_for_update().get(pk=indent.item_id)
    delta = case.affected_quantity if case.replacement_count > 0 else -case.affected_quantity
    entry = StockLedgerEntry.objects.create(
        item_id=indent.item_id,
        location=loc,
        entry_type="adjustment",
        quantity_delta=delta,
        source_ref_type="discrepancy",
        source_ref_id=case.pk,
        reason=f"Discrepancy {case.case_number} resolution: {notes}",
        actor_user_id=actor.user_id,
    )
    audit_record(
        actor=actor,
        action="stock.discrepancy_adjusted",
        target_type="stock_ledger",
        target_id=entry.pk,
        details={"case_id": case.pk, "quantity_delta": delta},
    )


def _apply_accounting_adjustment(actor, case: DiscrepancyCase) -> None:
    """Recalculate linked invoice eligible_amount and hold status atomically (AFR-PSM-055)."""
    po = case.grn.purchase_order
    if po is None:
        return
    other_open = (
        DiscrepancyCase.objects.filter(
            grn__purchase_order_id=po.pk,
            status__in=(sm.DISC_OPEN, sm.DISC_REPLACEMENT_AWAITED),
        )
        .exclude(pk=case.pk)
        .exists()
    )
    deduction = (
        Decimal("0.00")
        if case.replacement_count > 0
        else (Decimal(case.affected_quantity) * po.unit_price).quantize(Decimal("0.01"))
    )
    invoices = Invoice.objects.select_for_update().filter(
        purchase_order_id=po.pk,
        status__in=(sm.INV_SUBMITTED, sm.INV_ON_HOLD, sm.INV_VERIFIED),
    )
    for inv in invoices:
        old_inv_status = inv.status
        base = inv.eligible_amount if inv.eligible_amount > Decimal("0.00") else inv.billed_amount
        inv.eligible_amount = max(Decimal("0.00"), (base - deduction).quantize(Decimal("0.01")))
        if inv.eligible_amount == Decimal("0.00"):
            inv.status = sm.INV_ON_HOLD
            inv.hold_reason = f"Adjusted to 0.00 after discrepancy {case.case_number}"
        elif inv.status == sm.INV_ON_HOLD and not other_open:
            inv.status = sm.INV_VERIFIED
            inv.hold_reason = ""
        inv.save(update_fields=["eligible_amount", "status", "hold_reason", "updated_at"])
        audit_record(
            actor=actor,
            action="invoice.discrepancy_adjusted",
            target_type="invoice",
            target_id=inv.pk,
            from_state=old_inv_status,
            to_state=inv.status,
            details={"case_number": case.case_number, "eligible_amount": str(inv.eligible_amount)},
        )


def _notify_discrepancy_opened(actor, case: DiscrepancyCase, grn_number: str) -> None:
    """Record audit log and notify reporter when a discrepancy case is opened."""
    audit_record(
        actor=actor,
        action="discrepancy.reported",
        target_type="discrepancy",
        target_id=case.pk,
        to_state=sm.DISC_OPEN,
    )
    enqueue_notification(
        topic="discrepancy.reported",
        dedupe_key=f"discrepancy.reported:{case.pk}",
        recipient_user_id=actor.user_id,
        subject=f"Discrepancy case {case.case_number} opened",
        body=(
            f"Reported {case.discrepancy_type} on {grn_number} "
            f"for {case.affected_quantity} unit(s)."
        ),
        payload={"case_id": case.pk, "grn_id": case.grn_id},
    )


@transaction.atomic
def report_discrepancy(
    *,
    actor,
    grn_id: int,
    discrepancy_type: str,
    affected_quantity: int,
    description: str,
    requested_resolution: str,
    evidence_url: str = "",
    evidence_filename: str = "",
) -> DiscrepancyCase:
    """Log a delivery discrepancy with optional Drive evidence (PSM-UC-020)."""
    grn = scoping.grns_for(actor).select_for_update(of=("self",)).filter(pk=grn_id).first()
    if grn is None:
        raise NotFoundError("Goods receipt note not found.")
    if affected_quantity <= 0 or affected_quantity > grn.received_quantity:
        raise DomainError(
            f"Affected quantity must be between 1 and {grn.received_quantity}.",
            code="invalid_affected_quantity",
        )
    if not (description or "").strip():
        raise DomainError(
            "Describe the delivery discrepancy or damage.", code="description_required"
        )
    clean_url, clean_name = _clean_evidence(evidence_url, evidence_filename)
    case = DiscrepancyCase.objects.create(
        case_number=next_number("DSC"),
        grn=grn,
        reported_by_user_id=actor.user_id,
        discrepancy_type=discrepancy_type,
        affected_quantity=affected_quantity,
        description=description.strip(),
        evidence_url=clean_url,
        evidence_filename=clean_name,
        requested_resolution=requested_resolution,
        status=sm.DISC_OPEN,
    )
    _hold_po_invoices(grn.purchase_order_id, case.case_number)
    _notify_discrepancy_opened(actor, case, grn.grn_number)
    return case


@transaction.atomic
def add_communication(
    *, actor, case_id: int, sender_label: str, message: str
) -> DiscrepancyCommunication:
    """Append a vendor communication record to a discrepancy case (PSM-UC-032, AFR-PSM-052)."""
    case = scoping.discrepancies_for(actor).filter(pk=case_id).first()
    if case is None:
        raise NotFoundError("Discrepancy case not found.")
    if case.status == sm.DISC_CLOSED:
        raise ConflictError(
            "Cannot append communications to a closed discrepancy case.", code="case_closed"
        )
    if not (message or "").strip():
        raise DomainError("Enter the communication message before saving.", code="message_required")
    comm = DiscrepancyCommunication.objects.create(
        case=case,
        sender_label=(sender_label or "PS Admin").strip()[:120],
        message=message.strip(),
        recorded_by_user_id=actor.user_id,
    )
    audit_record(
        actor=actor,
        action="discrepancy.communication_logged",
        target_type="discrepancy",
        target_id=case.pk,
    )
    return comm


def _transition_case(
    actor,
    case: DiscrepancyCase,
    resolution_action: str,
    notes: str,
    inventory_adjusted: bool,
    accounting_adjusted: bool,
) -> None:
    """Apply the validated state transition and adjustments to a locked discrepancy case."""
    if resolution_action == "await_replacement":
        if case.replacement_count >= 1:
            raise ConflictError(
                "Only one replacement traversal is permitted per discrepancy case.",
                code="replacement_limit_reached",
            )
        with translate_errors():
            sm.resolve("discrepancy", case.status, sm.DISC_REPLACEMENT_AWAITED, sm.PS_ADMIN)
        case.status = sm.DISC_REPLACEMENT_AWAITED
        case.replacement_count += 1
        case.resolution_notes = notes
        case.save(update_fields=["status", "replacement_count", "resolution_notes", "updated_at"])
        return
    if resolution_action == "resolve":
        with translate_errors():
            sm.resolve("discrepancy", case.status, sm.DISC_RESOLVED, sm.PS_ADMIN)
        case.status = sm.DISC_RESOLVED
        case.resolution_notes = notes
        case.inventory_adjusted = inventory_adjusted
        case.accounting_adjusted = accounting_adjusted
        case.resolved_by_user_id = actor.user_id
        case.resolved_at = timezone.now()
        case.save()
        if inventory_adjusted:
            _apply_inventory_adjustment(actor, case, notes)
        if accounting_adjusted:
            _apply_accounting_adjustment(actor, case)
        return
    if resolution_action == "close":
        with translate_errors():
            sm.resolve("discrepancy", case.status, sm.DISC_CLOSED, sm.PS_ADMIN)
        case.status = sm.DISC_CLOSED
        case.resolution_notes = notes
        case.inventory_adjusted = case.inventory_adjusted or inventory_adjusted
        case.accounting_adjusted = case.accounting_adjusted or accounting_adjusted
        case.save()
        return
    raise DomainError(
        "Choose 'await_replacement', 'resolve', or 'close'.", code="invalid_resolution_action"
    )


@transaction.atomic
def resolve_case(
    *,
    actor,
    case_id: int,
    resolution_action: str,
    resolution_notes: str,
    inventory_adjusted: bool = False,
    accounting_adjusted: bool = False,
) -> DiscrepancyCase:
    """Resolve discrepancy via return/adjustment or one replacement (BW-PSM-06, 10)."""
    case = (
        scoping.discrepancies_for(actor).select_for_update(of=("self",)).filter(pk=case_id).first()
    )
    if case is None:
        raise NotFoundError("Discrepancy case not found.")
    notes = (resolution_notes or "").strip()
    if not notes:
        raise DomainError(
            "Provide resolution notes when updating this discrepancy case.", code="notes_required"
        )
    old_status = case.status
    _transition_case(actor, case, resolution_action, notes, inventory_adjusted, accounting_adjusted)
    audit_record(
        actor=actor,
        action=f"discrepancy.{resolution_action}",
        target_type="discrepancy",
        target_id=case.pk,
        from_state=old_status,
        to_state=case.status,
        details={
            "inventory_adjusted": case.inventory_adjusted,
            "accounting_adjusted": case.accounting_adjusted,
        },
    )
    return case
