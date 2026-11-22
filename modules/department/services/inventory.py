"""Inventory ledger (UC-DEPT-019) and the stock request lifecycle (CW-DEPT-01)."""

from __future__ import annotations

from django.db import IntegrityError, transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError
from modules.department.domain import rules
from modules.department.domain import state_machine as sm
from modules.department.domain.roles import DEPT_ADMIN, HOD, ActorContext
from modules.department.models import InventoryItem, StockMovement, StockRequest
from modules.department.selectors import scoping
from modules.department.selectors.actors import current_holders
from modules.department.services import notifications
from modules.department.services.common import (
    get_scoped,
    own_department,
    require_acting,
    translated,
)


@transaction.atomic
def add_item(
    ctx: ActorContext, *, name: str, unit: str, quantity: int, note: str = ""
) -> InventoryItem:
    """AFR-DEPT-007, AFR-DEPT-014: a new item arrives with its first receipt."""
    require_acting(ctx, DEPT_ADMIN)
    dept = own_department(ctx)
    with translated():
        rules.check_receipt(quantity)
    try:
        with transaction.atomic():
            item = InventoryItem.objects.create(
                department=dept, name=name.strip(), unit=unit or "unit", current_quantity=0
            )
    except IntegrityError as exc:
        raise ConflictError(
            f"{name} is already in this department's inventory; record a receipt instead.",
            code="item_exists",
        ) from exc
    return _receive(ctx, item, quantity, note)


@transaction.atomic
def receive(ctx: ActorContext, item_id: int, *, quantity: int, note: str = "") -> InventoryItem:
    """AFR-DEPT-008, AFR-DEPT-014: a receipt is a movement plus the running total."""
    require_acting(ctx, DEPT_ADMIN)
    item = get_scoped(scoping.inventory_items_for(ctx), item_id, lock=True, what="inventory item")
    with translated():
        rules.check_receipt(quantity)
    return _receive(ctx, item, quantity, note)


def _receive(ctx: ActorContext, item: InventoryItem, quantity: int, note: str) -> InventoryItem:
    StockMovement.objects.create(
        item=item, kind=StockMovement.RECEIPT, quantity=quantity, actor_id=ctx.user_id, note=note
    )
    item.current_quantity += quantity
    item.save(update_fields=["current_quantity", "updated_at"])
    return item


@transaction.atomic
def request_stock(
    ctx: ActorContext, *, item_id: int, quantity: int, purpose: str = ""
) -> StockRequest:
    """UC-DEPT-004: BR-DEPT-005 by permission and table, BR-DEPT-015 against the locked item."""
    with translated():
        sm.resolve("stock request", sm.NONE, sm.STOCK_PENDING, ctx.role)
    dept = own_department(ctx)
    item = (
        scoping.inventory_items_for(ctx).select_for_update(of=("self",)).filter(pk=item_id).first()
    )
    if item is None:
        raise NotFoundError("That inventory item does not exist in your department.")
    with translated():
        rules.check_availability(requested=quantity, available=item.current_quantity)
    req = StockRequest.objects.create(
        department=dept, item=item, requester_id=ctx.user_id, quantity=quantity, purpose=purpose
    )
    subject = f"[{dept.code}] Stock request #{req.pk}: {quantity} {item.unit} of {item.name}"
    notifications.enqueue(
        topic="stock_request.created",
        key=str(req.pk),
        subject=subject,
        recipients=current_holders([dept.pk], DEPT_ADMIN).values(),
        body="A new stock request was submitted.",
    )
    notifications.enqueue(
        topic="stock_request.pending_hod",
        key=str(req.pk),
        subject=subject,
        recipients=current_holders([dept.pk], HOD).values(),
        body="A stock request is waiting for your approval.",
    )
    return req


@transaction.atomic
def decide(ctx: ActorContext, request_id: int, *, approve: bool, reason: str = "") -> StockRequest:
    """UC-DEPT-005, BR-DEPT-006; Q14: no self-decision guard."""
    req = get_scoped(scoping.stock_requests_for(ctx), request_id, lock=True, what="stock request")
    target = sm.STOCK_APPROVED if approve else sm.STOCK_REJECTED
    with translated():
        sm.resolve("stock request", req.status, target, ctx.role)
    req.status, req.decided_by, req.decided_at, req.reason = (
        target,
        ctx.user_id,
        timezone.now(),
        reason,
    )
    req.save()
    if not approve:
        notifications.enqueue(
            topic="stock_request.rejected",
            key=str(req.pk),
            recipients=[req.requester_id],
            subject=f"Stock request #{req.pk} was rejected",
            body=reason or "The HOD rejected your stock request.",
        )
    return req


@transaction.atomic
def issue(ctx: ActorContext, request_id: int) -> StockRequest:
    """UC-DEPT-006: BR-DEPT-007, AFR-DEPT-013, BR-DEPT-016 and AFR-DEPT-043 in one transaction."""
    req = get_scoped(scoping.stock_requests_for(ctx), request_id, lock=True, what="stock request")
    with translated():
        sm.resolve("stock request", req.status, sm.STOCK_ISSUED, ctx.role)
    item = InventoryItem.objects.select_for_update().get(pk=req.item_id)
    if item.current_quantity < req.quantity:
        raise ConflictError(
            f"Only {item.current_quantity} {item.unit} left, fewer than the {req.quantity} "
            "approved. "
            "Record a receipt first; nothing was issued.",
            code="stock_exhausted",
        )
    item.current_quantity -= req.quantity
    item.save(update_fields=["current_quantity", "updated_at"])
    StockMovement.objects.create(
        item=item,
        kind=StockMovement.ISSUE,
        quantity=req.quantity,
        actor_id=ctx.user_id,
        stock_request=req,
    )
    req.status, req.issued_by, req.issued_at = sm.STOCK_ISSUED, ctx.user_id, timezone.now()
    req.save()
    notifications.enqueue(
        topic="stock_request.issued",
        key=str(req.pk),
        recipients=[req.requester_id],
        subject=f"Stock request #{req.pk} was issued",
        body=f"{req.quantity} {item.unit} of {item.name} were issued to you.",
    )
    return req
