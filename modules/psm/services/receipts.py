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
    if bool(purchase_order_id) == bool(internal_issue_id):
        raise DomainError(
            "Provide either purchase_order_id or internal_issue_id, not both.",
            code="grn_source_invalid",
        )
    po = issue = rep_case = None
    if purchase_order_id:
        po = (
            scoping.purchase_orders_for(actor)
            .select_for_update(of=("self",))
            .filter(pk=purchase_order_id)
            .first()
        )
        if po is None:
            raise NotFoundError("Purchase order not found.")
        if po.status in ("closed", "cancelled"):
            raise ConflictError(
                f"Cannot record a GRN for a purchase order in state '{po.status}'.",
                code="po_terminal",
            )
        ordered_qty = po.ordered_quantity
        prev_accepted = (
            GoodsReceiptNote.objects.filter(purchase_order=po).aggregate(
                t=Sum("accepted_quantity")
            )["t"]
            or 0
        )
        requestor_id = po.indent.user_id
    else:
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
        ordered_qty = issue.indent.quantity
        prev_accepted = (
            GoodsReceiptNote.objects.filter(internal_issue=issue).aggregate(
                t=Sum("accepted_quantity")
            )["t"]
            or 0
        )
        requestor_id = issue.indent.user_id

    if replacement_for_case_id:
        rep_case = (
            scoping.discrepancies_for(actor)
            .select_for_update(of=("self",))
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
        new_total = prev_accepted + accepted_quantity
        po.status = "delivered" if new_total >= po.ordered_quantity else "partially_delivered"
        po.actual_delivery_date = po.actual_delivery_date or timezone.now().date()
        po.save(update_fields=["status", "actual_delivery_date", "updated_at"])
    if rep_case is not None and accepted_quantity > 0:
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
    audit_record(
        actor=actor, action="grn.recorded", target_type="grn", target_id=grn.pk, to_state=grn_status
    )
    enqueue_notification(
        topic="grn.recorded",
        dedupe_key=f"grn.recorded:{grn.pk}",
        recipient_user_id=requestor_id,
        subject=f"GRN {grn.grn_number} recorded ({grn_status})",
        body=f"Inspection recorded {accepted_quantity} accepted, {rejected_quantity} rejected.",
        payload={"grn_id": grn.pk, "status": grn_status},
    )
    return grn


def _post_confirmed_stock(grn: GoodsReceiptNote, actor, now) -> None:
    """Post append-only stock entries on receipt confirmation (BR-PSM-009, 026)."""
    if grn.internal_issue_id:
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
        return
    po = grn.purchase_order
    if po.indent.item_id:
        loc = StockLocation.objects.filter(
            department__iexact=po.indent.department, is_central=False
        ).first()
        if loc is None:
            loc = StockLocation.objects.filter(is_central=True).first()
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
    _post_confirmed_stock(grn, actor, now)
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
    audit_record(
        actor=actor,
        action="grn.confirmed",
        target_type="grn",
        target_id=grn.pk,
        to_state="confirmed",
    )
    enqueue_notification(
        topic="grn.confirmed",
        dedupe_key=f"grn.confirmed:{grn.pk}",
        recipient_user_id=owner_id,
        subject=f"Delivery receipt confirmed for {grn.grn_number}",
        body=f"Confirmed {grn.accepted_quantity} accepted unit(s); final stock posting completed.",
        payload={"grn_id": grn.pk},
    )
    return grn
