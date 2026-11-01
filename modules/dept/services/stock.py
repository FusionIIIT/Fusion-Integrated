"""UC-DEPT-004..006 and CW-DEPT-01: request, decide, issue."""
from __future__ import annotations

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError
from modules.dept.domain import state_machine as sm
from modules.dept.models import InventoryItem, StockMovement, StockRequest
from modules.dept.services._errors import require, translated


@transaction.atomic
def add_inventory(*, actor, name: str, quantity: int, category: str = "",
                  unit: str = "pcs") -> InventoryItem:
    """Insertion into inventory, logged immutably (BR-DEPT-016). Adding to an
    existing item name tops it up rather than creating a duplicate."""
    require(actor, "dept.inventory.manage")
    name = (name or "").strip()
    if not name:
        raise ConflictError("An item needs a name.", code="name_required")
    if quantity <= 0:
        raise ConflictError("Quantity must be at least 1.",
                            code="quantity_invalid")
    item, _ = InventoryItem.objects.select_for_update().get_or_create(
        name=name, defaults={"category": category, "unit": unit, "quantity": 0})
    InventoryItem.objects.filter(pk=item.pk).update(
        quantity=F("quantity") + quantity)
    StockMovement.objects.create(item=item, kind=StockMovement.INSERT,
                                 quantity=quantity, actor_user_id=actor.user_id)
    item.refresh_from_db()
    return item


@transaction.atomic
def request_stock(*, actor, item_id: int, quantity: int,
                  purpose: str = "") -> StockRequest:
    require(actor, "dept.stock_request.create")                   # BR-DEPT-005
    item = InventoryItem.objects.select_for_update().filter(pk=item_id).first()
    if item is None:
        raise NotFoundError("No such inventory item.")
    if quantity <= 0:
        raise ConflictError("Quantity must be at least 1.",
                            code="quantity_invalid")
    if quantity > item.quantity:                                  # BR-DEPT-015
        raise ConflictError(
            f"Only {item.quantity} {item.unit} of {item.name} in stock.",
            code="insufficient_stock")
    return StockRequest.objects.create(
        item=item, requested_by_user_id=actor.user_id, quantity=quantity,
        purpose=purpose)


def _locked(request_id: int) -> StockRequest:
    stock_request = (StockRequest.objects.select_for_update()
                     .select_related("item").filter(pk=request_id).first())
    if stock_request is None:
        raise NotFoundError("No such stock request.")
    return stock_request


@transaction.atomic
def decide(*, request_id: int, actor, approve: bool,
           note: str = "") -> StockRequest:
    stock_request = _locked(request_id)
    target = sm.APPROVED if approve else sm.REJECTED
    with translated():
        sm.validate_transition(sm.STOCK_TRANSITIONS, stock_request.status,
                               target, actor.permissions)          # BR-DEPT-006
    stock_request.status = target
    stock_request.decided_by_user_id = actor.user_id
    stock_request.decided_at = timezone.now()
    stock_request.decision_note = note
    stock_request.save()
    return stock_request


@transaction.atomic
def issue(*, request_id: int, actor) -> StockRequest:
    """BR-DEPT-007 + 016: only an approved request, decrement and log."""
    stock_request = _locked(request_id)
    with translated():
        sm.validate_transition(sm.STOCK_TRANSITIONS, stock_request.status,
                               sm.ISSUED, actor.permissions)

    # Stock may have been issued to someone else since the request was made.
    item = InventoryItem.objects.select_for_update().get(pk=stock_request.item_id)
    if stock_request.quantity > item.quantity:
        raise ConflictError(
            f"Only {item.quantity} {item.unit} of {item.name} left.",
            code="insufficient_stock")
    InventoryItem.objects.filter(pk=item.pk).update(
        quantity=F("quantity") - stock_request.quantity)
    StockMovement.objects.create(
        item=item, kind=StockMovement.ISSUE, quantity=stock_request.quantity,
        request=stock_request, recipient_user_id=stock_request.requested_by_user_id,
        actor_user_id=actor.user_id)

    stock_request.status = sm.ISSUED
    stock_request.issued_by_user_id = actor.user_id
    stock_request.issued_at = timezone.now()
    stock_request.save()
    return stock_request
