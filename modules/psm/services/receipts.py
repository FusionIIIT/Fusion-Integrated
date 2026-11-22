# Delivery inspection, GRN recording, and receipt confirmation (PSM-UC-002, 028).
from __future__ import annotations

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from core.api.exceptions import ConflictError, DomainError, NotFoundError
from modules.psm.domain import receipt_rules as rr
from modules.psm.domain import state_machine as sm
from modules.psm.models import (
    DiscrepancyCase,
    GoodsReceiptNote,
    StockLedgerEntry,
    StockLocation,
    StockReservation,
)
from modules.psm.selectors import scoping
from modules.psm.services.common import (
    actor_lane_for,
    audit_record,
    enqueue_notification,
    next_number,
    translate_errors,
)
from modules.psm.services.indents import transition_indent


def _load_grn_source(actor, purchase_order_id: int | None, internal_issue_id: int | None):
    """Lock and validate either the PO or internal issue for a new GRN."""
    if bool(purchase_order_id) == bool(internal_issue_id):
        raise DomainError(
            "Provide either purchase_order_id or internal_issue_id, not both.",
            code="grn_source_invalid",
        )
    if purchase_order_id:
        po = (
            scoping.purchase_orders_for(actor)
            .select_for_update(of=("self",))
            .filter(pk=purchase_order_id)
            .first()
        )
        if po is None:
            raise NotFoundError("Purchase order not found.")
        if po.status in sm.PO_TERMINAL:
            raise ConflictError(
                f"Cannot record a GRN for a purchase order in state '{po.status}'.",
                code="po_terminal",
            )
        prev = GoodsReceiptNote.objects.filter(purchase_order=po).aggregate(
            t=Sum("accepted_quantity")
        )["t"]
        return po, None, po.ordered_quantity, prev or 0, po.indent.user_id
    issue = (
        scoping.internal_issues_for(actor)
        .select_for_update(of=("self",))
        .filter(pk=internal_issue_id)
        .first()
    )
    if issue is None:
        raise NotFoundError("Internal issue not found.")
    if issue.status not in ("dispatched", "grn_recorded"):
        raise ConflictError(
            f"Dispatch the internal issue before recording a GRN (current: '{issue.status}').",
            code="issue_not_dispatched",
        )
    prev = GoodsReceiptNote.objects.filter(internal_issue=issue).aggregate(
        t=Sum("accepted_quantity")
    )["t"]
    return None, issue, issue.indent.quantity, prev or 0, issue.indent.user_id


def _load_replacement_case(actor, replacement_for_case_id: int | None, po, issue):
    """Lock and validate an optional replacement discrepancy case matches the GRN source (R2-03)."""
    if not replacement_for_case_id:
        return None
    rep_case = (
        scoping.discrepancies_for(actor)
        .select_for_update(of=("self",))
        .select_related("grn")
        .filter(pk=replacement_for_case_id)
        .first()
    )
    if rep_case is None:
        raise NotFoundError("Discrepancy case not found.")
    if rep_case.status != sm.DISC_REPLACEMENT_AWAITED:
        raise ConflictError(
            "Replacement GRN requires a case in replacement_awaited state.",
            code="not_awaiting_replacement",
        )
    po_id = po.pk if po is not None else None
    issue_id = issue.pk if issue is not None else None
    if rep_case.grn.purchase_order_id != po_id or rep_case.grn.internal_issue_id != issue_id:
        raise ConflictError(
            "Replacement GRN must belong to the same purchase order or internal issue as the case.",
            code="replacement_source_mismatch",
        )
    return rep_case


def _update_grn_linked_records(
    *, actor, grn: GoodsReceiptNote, po, issue, rep_case, prev_accepted: int, grn_status: str
) -> None:
    """Propagate GRN inspection results to linked internal issue, PO, and replacement case."""
    if issue is not None and grn_status in ("accepted", "partial"):
        issue.status = "grn_recorded"
        issue.save(update_fields=["status", "updated_at"])
        if issue.indent.status == sm.DISPATCHED:
            transition_indent(
                indent=issue.indent,
                to_status=sm.GRN_RECORDED,
                actor=actor,
                actor_lane=actor_lane_for(actor),
                action="grn.recorded",
                reason=f"GRN {grn.grn_number} recorded ({grn_status})",
            )
    if po is not None and grn_status in ("accepted", "partial"):
        new_total = prev_accepted + grn.accepted_quantity
        next_po_status = (
            sm.PO_DELIVERED if new_total >= po.ordered_quantity else sm.PO_PARTIALLY_DELIVERED
        )
        if po.status != next_po_status:
            with translate_errors():
                sm.resolve("purchase_order", po.status, next_po_status, sm.RECEIVING_ACTOR)
            po.status = next_po_status
        po.actual_delivery_date = po.actual_delivery_date or timezone.now().date()
        po.save(update_fields=["status", "actual_delivery_date", "updated_at"])
    if rep_case is not None and grn.accepted_quantity > 0:
        rep_case.status = sm.DISC_RESOLVED
        rep_case.resolved_by_user_id = actor.user_id
        rep_case.resolved_at = timezone.now()
        rep_case.resolution_notes = (
            rep_case.resolution_notes + f" Replacement received via {grn.grn_number}."
        ).strip()
        rep_case.save(
            update_fields=[
                "status",
                "resolved_by_user_id",
                "resolved_at",
                "resolution_notes",
                "updated_at",
            ]
        )


def _notify_grn_event(actor, grn: GoodsReceiptNote, requestor_id: int, event: str) -> None:
    """Record audit entry and requestor notification for GRN recorded or confirmed."""
    audit_record(
        actor=actor, action=f"grn.{event}", target_type="grn", target_id=grn.pk, to_state=grn.status
    )
    if event == "recorded":
        subject = f"GRN {grn.grn_number} recorded ({grn.status})"
        body = (
            f"Inspection recorded {grn.accepted_quantity} accepted, "
            f"{grn.rejected_quantity} rejected."
        )
        payload = {"grn_id": grn.pk, "status": grn.status}
    else:
        subject = f"Delivery receipt confirmed for {grn.grn_number}"
        body = f"Confirmed {grn.accepted_quantity} accepted unit(s); final stock posting completed."
        payload = {"grn_id": grn.pk}
    enqueue_notification(
        topic=f"grn.{event}",
        dedupe_key=f"grn.{event}:{grn.pk}",
        recipient_user_id=requestor_id,
        subject=subject,
        body=body,
        payload=payload,
    )


@transaction.atomic
def record_grn(
    *,
    actor,
    received_quantity: int,
    accepted_quantity: int,
    rejected_quantity: int = 0,
    purchase_order_id: int | None = None,
    internal_issue_id: int | None = None,
    replacement_for_case_id: int | None = None,
    inspection_notes: str = "",
) -> GoodsReceiptNote:
    """Inspect delivered goods and record an accepted, partial, or rejected GRN (PSM-UC-028)."""
    po, issue, ordered_qty, prev_accepted, requestor_id = _load_grn_source(
        actor, purchase_order_id, internal_issue_id
    )
    rep_case = _load_replacement_case(actor, replacement_for_case_id, po, issue)
    with translate_errors():
        grn_status = rr.validate_grn_quantities(
            ordered_quantity=ordered_qty,
            previously_accepted=prev_accepted,
            received_quantity=received_quantity,
            accepted_quantity=accepted_quantity,
            rejected_quantity=rejected_quantity,
        )
    grn = GoodsReceiptNote.objects.create(
        grn_number=next_number("GRN"),
        purchase_order=po,
        internal_issue=issue,
        replacement_for_case=rep_case,
        inspected_by_user_id=actor.user_id,
        received_quantity=received_quantity,
        accepted_quantity=accepted_quantity,
        rejected_quantity=rejected_quantity,
        inspection_notes=inspection_notes.strip(),
        status=grn_status,
    )
    _update_grn_linked_records(
        actor=actor,
        grn=grn,
        po=po,
        issue=issue,
        rep_case=rep_case,
        prev_accepted=prev_accepted,
        grn_status=grn_status,
    )
    _notify_grn_event(actor, grn, requestor_id, "recorded")
    return grn


def _post_internal_issue_stock(grn: GoodsReceiptNote, actor, now) -> None:
    """Consume reservation, deduct stock, and fulfill an internal-issue indent."""
    issue = grn.internal_issue
    if issue.reservation_id:
        StockReservation.objects.filter(pk=issue.reservation_id, status="active").update(
            status="consumed", released_at=now
        )
    if issue.indent.item_id:
        StockLedgerEntry.objects.create(
            item_id=issue.indent.item_id,
            location=issue.location,
            entry_type="internal_issue_post",
            quantity_delta=-grn.accepted_quantity,
            source_ref_type="grn",
            source_ref_id=grn.pk,
            reason=f"Confirmed internal issue GRN {grn.grn_number}",
            actor_user_id=actor.user_id,
        )
    issue.status = "completed"
    issue.save(update_fields=["status", "updated_at"])
    if issue.indent.status == sm.GRN_RECORDED:
        transition_indent(
            indent=issue.indent,
            to_status=sm.FULFILLED,
            actor=actor,
            actor_lane=sm.EMPLOYEE,
            action="indent.fulfilled",
            reason=f"Internal issue receipt confirmed ({grn.grn_number})",
        )


def _post_po_receipt_stock(grn: GoodsReceiptNote, actor) -> None:
    """Post positive stock receipt for a confirmed PO GRN and fulfill completed indents."""
    po = grn.purchase_order
    if po.indent.item_id:
        loc = (
            StockLocation.objects.filter(
                department__iexact=po.indent.department, is_central=False
            ).first()
            or StockLocation.objects.filter(is_central=True).first()
        )
        if loc is not None:
            StockLedgerEntry.objects.create(
                item_id=po.indent.item_id,
                location=loc,
                entry_type="receipt_post",
                quantity_delta=grn.accepted_quantity,
                source_ref_type="grn",
                source_ref_id=grn.pk,
                reason=f"Confirmed PO receipt {grn.grn_number} ({po.po_number})",
                actor_user_id=actor.user_id,
            )
    confirmed_total = (
        GoodsReceiptNote.objects.filter(purchase_order=po, status="confirmed").aggregate(
            t=Sum("accepted_quantity")
        )["t"]
        or 0
    )
    if (
        confirmed_total + grn.accepted_quantity >= po.ordered_quantity
        and po.indent.status == sm.PO_ISSUED
    ):
        transition_indent(
            indent=po.indent,
            to_status=sm.FULFILLED,
            actor=actor,
            actor_lane=sm.EMPLOYEE,
            action="indent.fulfilled",
            reason=f"All ordered units confirmed via {grn.grn_number}",
        )


@transaction.atomic
def confirm_receipt(*, actor, grn_id: int) -> GoodsReceiptNote:
    """Requestor confirms receipt and posts final stock (PSM-UC-002)."""
    grn = scoping.grns_for(actor).select_for_update(of=("self",)).filter(pk=grn_id).first()
    if grn is None:
        raise NotFoundError("Goods receipt note not found.")
    owner_id = (
        grn.purchase_order.indent.user_id
        if grn.purchase_order_id
        else grn.internal_issue.indent.user_id
    )
    if owner_id != actor.user_id:
        raise NotFoundError("Goods receipt note not found.")
    has_open_disc = (
        DiscrepancyCase.objects.filter(grn=grn)
        .exclude(status__in=(sm.DISC_RESOLVED, sm.DISC_CLOSED))
        .exists()
    )
    with translate_errors():
        rr.ensure_can_post_stock(
            accepted_quantity=grn.accepted_quantity,
            has_open_discrepancy=has_open_disc,
            already_posted=grn.stock_posted,
        )
    now = timezone.now()
    if grn.internal_issue_id:
        _post_internal_issue_stock(grn, actor, now)
    else:
        _post_po_receipt_stock(grn, actor)
    grn.status = "confirmed"
    grn.confirmed_by_user_id = actor.user_id
    grn.confirmed_at = now
    grn.stock_posted = True
    grn.stock_posted_at = now
    grn.save(
        update_fields=[
            "status",
            "confirmed_by_user_id",
            "confirmed_at",
            "stock_posted",
            "stock_posted_at",
            "updated_at",
        ]
    )
    _notify_grn_event(actor, grn, owner_id, "confirmed")
    return grn
