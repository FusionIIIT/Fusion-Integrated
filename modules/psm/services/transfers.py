# Inter-departmental stock transfers (PSM-UC-021, 033, 034, BW-PSM-08).
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, DomainError, NotFoundError
from modules.psm.domain import state_machine as sm
from modules.psm.models import (
    StockItem,
    StockLedgerEntry,
    StockLocation,
    StockReservation,
    StockTransfer,
)
from modules.psm.selectors import scoping
from modules.psm.selectors.stock import stock_balances_for_item
from modules.psm.services.common import (
    actor_lane_for,
    audit_record,
    enqueue_notification,
    next_number,
    translate_errors,
)


@transaction.atomic
def request_transfer(
    *,
    actor,
    item_id: int,
    source_location_id: int,
    destination_location_id: int,
    quantity: int,
    notes: str = "",
) -> StockTransfer:
    """Create an inter-departmental stock transfer request (PSM-UC-021, AFR-PSM-067)."""
    if quantity <= 0:
        raise DomainError("Transfer quantity must be greater than zero.", code="invalid_quantity")
    if source_location_id == destination_location_id:
        raise DomainError(
            "Source and destination locations must be different.", code="same_transfer_location"
        )
    item = StockItem.objects.filter(pk=item_id, is_active=True).first()
    if item is None:
        raise NotFoundError("Stock item not found.")
    source = StockLocation.objects.filter(pk=source_location_id).first()
    dest = scoping.stock_locations_for(actor).filter(pk=destination_location_id).first()
    if source is None or dest is None:
        raise NotFoundError("Source or destination stock location not found.")
    balances = {b.location_id: b for b in stock_balances_for_item(item.pk)}
    src_bal = balances.get(source.pk)
    if src_bal is None or src_bal.allocable < quantity:
        avail = src_bal.allocable if src_bal else 0
        raise ConflictError(
            f"Location {source.code} has only {avail} allocable unit(s); requested {quantity}.",
            code="insufficient_source_stock",
        )
    transfer = StockTransfer.objects.create(
        transfer_number=next_number("TRF"),
        item=item,
        source_location=source,
        destination_location=dest,
        quantity=quantity,
        status=sm.TRANSFER_REQUESTED,
        requested_by_user_id=actor.user_id,
        notes=notes.strip(),
    )
    audit_record(
        actor=actor,
        action="transfer.requested",
        target_type="stock_transfer",
        target_id=transfer.pk,
        to_state=sm.TRANSFER_REQUESTED,
    )
    return transfer


@transaction.atomic
def dispatch_transfer(*, actor, transfer_id: int) -> StockTransfer:
    """Reserve source stock and dispatch transfer (PSM-UC-033, BR-PSM-013)."""
    transfer = (
        scoping.transfers_for(actor).select_for_update(of=("self",)).filter(pk=transfer_id).first()
    )
    if transfer is None:
        raise NotFoundError("Stock transfer not found.")
    with translate_errors():
        sm.resolve("transfer", transfer.status, sm.TRANSFER_DISPATCHED, actor_lane_for(actor))
    # Serialize concurrent reservations on the same StockItem row (BR-PSM-013).
    StockItem.objects.select_for_update().get(pk=transfer.item_id)
    balances = {b.location_id: b for b in stock_balances_for_item(transfer.item_id)}
    src_bal = balances.get(transfer.source_location_id)
    if src_bal is None or src_bal.allocable < transfer.quantity:
        avail = src_bal.allocable if src_bal else 0
        raise ConflictError(
            f"Source location {transfer.source_location.code} only has {avail} allocable unit(s).",
            code="insufficient_source_stock",
        )
    reservation = StockReservation.objects.create(
        item=transfer.item,
        location=transfer.source_location,
        quantity=transfer.quantity,
        purpose="stock_transfer",
        transfer_id=transfer.pk,
        status="active",
        reserved_by_user_id=actor.user_id,
    )
    transfer.reservation = reservation
    transfer.status = sm.TRANSFER_DISPATCHED
    transfer.dispatched_by_user_id = actor.user_id
    transfer.dispatched_at = timezone.now()
    transfer.save(
        update_fields=[
            "reservation",
            "status",
            "dispatched_by_user_id",
            "dispatched_at",
            "updated_at",
        ]
    )
    audit_record(
        actor=actor,
        action="transfer.dispatched",
        target_type="stock_transfer",
        target_id=transfer.pk,
        from_state=sm.TRANSFER_REQUESTED,
        to_state=sm.TRANSFER_DISPATCHED,
    )
    enqueue_notification(
        topic="transfer.dispatched",
        dedupe_key=f"transfer.dispatched:{transfer.pk}",
        recipient_user_id=transfer.requested_by_user_id,
        subject=f"Stock transfer {transfer.transfer_number} dispatched",
        body=f"{transfer.quantity} unit(s) dispatched from {transfer.source_location.code}.",
        payload={"transfer_id": transfer.pk},
    )
    return transfer


@transaction.atomic
def confirm_transfer(*, actor, transfer_id: int) -> StockTransfer:
    """Confirm transfer receipt and post dual ledgers (PSM-UC-034, BR-PSM-027)."""
    transfer = (
        scoping.transfers_for(actor).select_for_update(of=("self",)).filter(pk=transfer_id).first()
    )
    if transfer is None:
        raise NotFoundError("Stock transfer not found.")
    with translate_errors():
        sm.resolve("transfer", transfer.status, sm.TRANSFER_COMPLETED, sm.DEPT_ADMIN)
    dept = scoping.actor_department(actor)
    if dept and transfer.destination_location.department.lower() != dept.lower():
        raise ConflictError(
            "Only the destination department admin may confirm receipt of this transfer.",
            code="wrong_destination_dept",
        )
    StockItem.objects.select_for_update().get(pk=transfer.item_id)
    now = timezone.now()
    if transfer.reservation_id:
        StockReservation.objects.filter(pk=transfer.reservation_id, status="active").update(
            status="consumed", released_at=now
        )
    StockLedgerEntry.objects.create(
        item=transfer.item,
        location=transfer.source_location,
        entry_type="transfer_out",
        quantity_delta=-transfer.quantity,
        source_ref_type="stock_transfer",
        source_ref_id=transfer.pk,
        reason=f"Transfer {transfer.transfer_number} to {transfer.destination_location.code}",
        actor_user_id=actor.user_id,
    )
    StockLedgerEntry.objects.create(
        item=transfer.item,
        location=transfer.destination_location,
        entry_type="transfer_in",
        quantity_delta=transfer.quantity,
        source_ref_type="stock_transfer",
        source_ref_id=transfer.pk,
        reason=f"Transfer {transfer.transfer_number} from {transfer.source_location.code}",
        actor_user_id=actor.user_id,
    )
    transfer.status = sm.TRANSFER_COMPLETED
    transfer.confirmed_by_user_id = actor.user_id
    transfer.confirmed_at = now
    transfer.save(update_fields=["status", "confirmed_by_user_id", "confirmed_at", "updated_at"])
    audit_record(
        actor=actor,
        action="transfer.completed",
        target_type="stock_transfer",
        target_id=transfer.pk,
        from_state=sm.TRANSFER_DISPATCHED,
        to_state=sm.TRANSFER_COMPLETED,
    )
    return transfer


@transaction.atomic
def cancel_transfer(*, actor, transfer_id: int) -> StockTransfer:
    """Cancel a pending stock transfer request."""
    transfer = (
        scoping.transfers_for(actor).select_for_update(of=("self",)).filter(pk=transfer_id).first()
    )
    if transfer is None:
        raise NotFoundError("Stock transfer not found.")
    with translate_errors():
        sm.resolve("transfer", transfer.status, sm.TRANSFER_CANCELLED, actor_lane_for(actor))
    transfer.status = sm.TRANSFER_CANCELLED
    transfer.save(update_fields=["status", "updated_at"])
    audit_record(
        actor=actor,
        action="transfer.cancelled",
        target_type="stock_transfer",
        target_id=transfer.pk,
        from_state=sm.TRANSFER_REQUESTED,
        to_state=sm.TRANSFER_CANCELLED,
    )
    return transfer
