# Stock check, reservation, internal issue dispatch, and ledger adjustments (PSM-UC-007, 008, 009).
from __future__ import annotations

from django.db import IntegrityError, transaction
from django.db.models import Sum
from django.utils import timezone

from core.api.exceptions import ConflictError, DomainError, NotFoundError
from modules.psm.domain import state_machine as sm
from modules.psm.domain import stock_rules as sr
from modules.psm.models import (
    DiscrepancyCase,
    InternalIssue,
    StockItem,
    StockLedgerEntry,
    StockLocation,
    StockReservation,
)
from modules.psm.selectors import scoping
from modules.psm.selectors.stock import stock_balances_for_item
from modules.psm.services.common import audit_record, enqueue_notification, translate_errors
from modules.psm.services.indents import transition_indent


@transaction.atomic
def create_stock_item(
    *, actor, sku: str, name: str, category: str = "", unit: str = "unit", description: str = ""
) -> StockItem:
    """Create a stock catalog item."""
    try:
        item = StockItem.objects.create(
            sku=sku.strip().upper(),
            name=name.strip(),
            category=category.strip(),
            unit=unit.strip() or "unit",
            description=description.strip(),
        )
    except IntegrityError as exc:
        raise ConflictError(
            "A stock item with that SKU already exists.", code="sku_exists"
        ) from exc
    audit_record(
        actor=actor, action="stock_item.created", target_type="stock_item", target_id=item.pk
    )
    return item


@transaction.atomic
def create_stock_location(
    *, actor, code: str, name: str, department: str, is_central: bool = False
) -> StockLocation:
    """Create a departmental or central store location."""
    try:
        loc = StockLocation.objects.create(
            code=code.strip().upper(),
            name=name.strip(),
            department="CENTRAL" if is_central else department.strip(),
            is_central=is_central,
        )
    except IntegrityError as exc:
        raise ConflictError(
            "A stock location with that code already exists.", code="location_exists"
        ) from exc
    audit_record(
        actor=actor, action="stock_location.created", target_type="stock_location", target_id=loc.pk
    )
    return loc


@transaction.atomic
def check_and_reserve(*, actor, indent_id: int) -> tuple[object, StockReservation | None]:
    """Check departmental then central stock and reserve (PSM-UC-007, BR-PSM-003, 013)."""
    indent = scoping.indents_for(actor).select_for_update(of=("self",)).filter(pk=indent_id).first()
    if indent is None:
        raise NotFoundError("Indent not found.")
    if indent.item_id is None:
        transition_indent(
            indent=indent,
            to_status=sm.EXTERNAL_REQUIRED,
            actor=actor,
            actor_lane=sm.DEPT_ADMIN,
            action="indent.stock_checked",
            reason="No linked stock catalog item; routed to external procurement",
        )
        return indent, None
    # Lock the StockItem row so concurrent reservations serialize cleanly (BR-PSM-013).
    StockItem.objects.select_for_update().get(pk=indent.item_id)
    balances = stock_balances_for_item(indent.item_id)
    with translate_errors():
        chosen = sr.select_allocation_location(balances, indent.department, indent.quantity)
    if chosen is None:
        transition_indent(
            indent=indent,
            to_status=sm.EXTERNAL_REQUIRED,
            actor=actor,
            actor_lane=sm.DEPT_ADMIN,
            action="indent.stock_checked",
            reason="Insufficient departmental and central stock",
        )
        return indent, None
    reservation = StockReservation.objects.create(
        item_id=indent.item_id,
        location_id=chosen.location_id,
        quantity=indent.quantity,
        purpose="internal_issue",
        indent_id=indent.pk,
        status="active",
        reserved_by_user_id=actor.user_id,
    )
    transition_indent(
        indent=indent,
        to_status=sm.STOCK_RESERVED,
        actor=actor,
        actor_lane=sm.DEPT_ADMIN,
        action="indent.stock_reserved",
        reason=f"Reserved {indent.quantity} unit(s) at {chosen.location_code}",
        extra_updates={"procurement_method": "internal"},
    )
    enqueue_notification(
        topic="indent.stock_available",
        dedupe_key=f"indent.stock_available:{indent.pk}:{reservation.pk}",
        recipient_user_id=indent.user_id,
        subject=f"Stock reserved for indent {indent.indent_number}",
        body=f"{indent.quantity} unit(s) reserved at {chosen.location_code} for internal issue.",
        payload={"indent_id": indent.pk, "location_code": chosen.location_code},
    )
    return indent, reservation


@transaction.atomic
def schedule_picking(
    *, actor, issue_id: int, picking_scheduled_at=None, dispatch_scheduled_at=None
) -> InternalIssue:
    """Schedule picking for an approved internal issue (PSM-UC-009, AFR-PSM-017)."""
    issue = (
        scoping.internal_issues_for(actor)
        .select_for_update(of=("self",))
        .filter(pk=issue_id)
        .first()
    )
    if issue is None:
        raise NotFoundError("Internal issue not found.")
    if issue.status not in ("approved", "picking_scheduled"):
        raise ConflictError(
            f"Cannot schedule picking while internal issue is '{issue.status}'.",
            code="invalid_issue_state",
        )
    issue.picking_scheduled_at = picking_scheduled_at or timezone.now()
    if dispatch_scheduled_at is not None:
        issue.dispatch_scheduled_at = dispatch_scheduled_at
    issue.status = "picking_scheduled"
    issue.save(
        update_fields=["picking_scheduled_at", "dispatch_scheduled_at", "status", "updated_at"]
    )
    audit_record(
        actor=actor,
        action="internal_issue.picking_scheduled",
        target_type="internal_issue",
        target_id=issue.pk,
        to_state="picking_scheduled",
    )
    return issue


@transaction.atomic
def dispatch_internal_issue(*, actor, issue_id: int) -> InternalIssue:
    """Dispatch reserved stock for internal issue (PSM-UC-009, BW-PSM-01)."""
    issue = (
        scoping.internal_issues_for(actor)
        .select_for_update(of=("self",))
        .filter(pk=issue_id)
        .first()
    )
    if issue is None:
        raise NotFoundError("Internal issue not found.")
    if issue.status not in ("approved", "picking_scheduled"):
        raise ConflictError(
            f"Cannot dispatch internal issue in state '{issue.status}'.", code="invalid_issue_state"
        )
    if issue.reservation.status != "active":
        raise ConflictError(
            "The stock reservation for this internal issue is no longer active.",
            code="reservation_inactive",
        )
    now = timezone.now()
    issue.dispatched_at = now
    issue.dispatch_scheduled_at = issue.dispatch_scheduled_at or now
    issue.dispatched_by_user_id = actor.user_id
    issue.status = "dispatched"
    issue.save(
        update_fields=[
            "dispatched_at",
            "dispatch_scheduled_at",
            "dispatched_by_user_id",
            "status",
            "updated_at",
        ]
    )
    transition_indent(
        indent=issue.indent,
        to_status=sm.DISPATCHED,
        actor=actor,
        actor_lane=sm.DEPT_ADMIN,
        action="internal_issue.dispatched",
        reason=f"Dispatched from {issue.location.code}",
    )
    enqueue_notification(
        topic="internal_issue.dispatched",
        dedupe_key=f"internal_issue.dispatched:{issue.pk}",
        recipient_user_id=issue.indent.user_id,
        subject=f"Internal issue dispatched for {issue.indent.indent_number}",
        body="Requested items dispatched; ready for inspection and receipt confirmation.",
        payload={"internal_issue_id": issue.pk, "indent_id": issue.indent_id},
    )
    return issue


@transaction.atomic
def record_adjustment(
    *,
    actor,
    item_id: int,
    location_id: int,
    quantity_delta: int,
    reason: str,
    entry_type: str = "adjustment",
    source_ref_type: str = "manual",
    source_ref_id: int | None = None,
) -> StockLedgerEntry:
    """Append an authorized stock adjustment (PSM-UC-008, BR-PSM-009)."""
    if not (reason or "").strip():
        raise DomainError("Provide a reason for this stock adjustment.", code="reason_required")
    item = StockItem.objects.select_for_update().filter(pk=item_id, is_active=True).first()
    if item is None:
        raise NotFoundError("Stock item not found.")
    location = scoping.stock_locations_for(actor).filter(pk=location_id).first()
    if location is None:
        raise NotFoundError("Stock location not found.")
    if source_ref_type == "grn" and source_ref_id is not None:
        has_open = (
            DiscrepancyCase.objects.filter(grn_id=source_ref_id)
            .exclude(status__in=(sm.DISC_RESOLVED, sm.DISC_CLOSED))
            .exists()
        )
        if has_open:
            raise ConflictError(
                "Resolve the open discrepancy case before posting a stock adjustment for this GRN.",
                code="unresolved_discrepancy",
            )
    on_hand = (
        StockLedgerEntry.objects.filter(item=item, location=location).aggregate(
            t=Sum("quantity_delta")
        )["t"]
        or 0
    )
    reserved = (
        StockReservation.objects.filter(item=item, location=location, status="active").aggregate(
            t=Sum("quantity")
        )["t"]
        or 0
    )
    with translate_errors():
        sr.ensure_adjustment_non_negative(on_hand, reserved, quantity_delta)
    entry = StockLedgerEntry.objects.create(
        item=item,
        location=location,
        entry_type=entry_type,
        quantity_delta=quantity_delta,
        source_ref_type=source_ref_type,
        source_ref_id=source_ref_id,
        reason=reason.strip(),
        actor_user_id=actor.user_id,
    )
    audit_record(
        actor=actor,
        action="stock.adjusted",
        target_type="stock_ledger",
        target_id=entry.pk,
        details={"item_id": item.pk, "location_id": location.pk, "delta": quantity_delta},
    )
    return entry
