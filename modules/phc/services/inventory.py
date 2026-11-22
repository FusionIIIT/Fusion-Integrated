"""Stock and requisition writes (PHC-BR-07, PHC-BR-10, PHC-BR-11)."""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import (
    BadRequestError,
    ConflictError,
    DomainError,
    NotFoundError,
)
from modules.phc.domain.policy import (
    ALREADY_DONE_MESSAGE,
    STOCK_MESSAGE,
    STOCK_OVERFLOW_MESSAGE,
    UNKNOWN_ITEM_MESSAGE,
    WAITING_MESSAGE,
    StockOverflow,
    is_low_stock,
    stock_after_adjustment,
)
from modules.phc.domain.state_machine import REQUISITION_EXPECTED, next_requisition_state
from modules.phc.models import (
    InventoryItem,
    Patient,
    Requisition,
    RequisitionItem,
    StockAdjustment,
)
from modules.phc.services import audit, notifications

ITEM_NOT_FOUND = "No such stock item. Refresh the inventory list and try again."
REQ_NOT_FOUND = "No requisition was found. Refresh the list and try again."


@transaction.atomic
def adjust_stock(actor, validated: dict):
    """Apply an add/deduct under a row lock; never silently floor a deduction."""
    item = (InventoryItem.objects
            .select_for_update().filter(pk=validated["item_id"]).first())
    if item is None:
        raise NotFoundError(ITEM_NOT_FOUND, code="not_found")
    try:
        new_level = stock_after_adjustment(
            item.quantity, validated["quantity"], validated["direction"])
    except StockOverflow as exc:
        raise BadRequestError(STOCK_OVERFLOW_MESSAGE,
                              code="stock_overflow") from exc
    if new_level is None:
        raise DomainError(STOCK_MESSAGE, code="invalid_deduction")
    item.quantity = new_level
    item.save()
    adjustment = StockAdjustment.objects.create(
        item=item, quantity=validated["quantity"],
        direction=validated["direction"],
        user_id=getattr(actor, "user_id", None),
        adjusted_by=getattr(actor, "user_id", None),
        reason=validated.get("reason", ""),
    )
    below = is_low_stock(item.quantity, item.reorder_threshold)
    audit.record(actor, "inventory.adjust", "inventory", item.pk,
                 {"direction": validated["direction"],
                  "quantity": validated["quantity"], "below_threshold": below})
    if below:
        notifications.low_stock_notice(item, item.quantity)
    return adjustment, below


@transaction.atomic
def create_item(validated: dict) -> InventoryItem:
    return InventoryItem.objects.create(
        name=validated["name"],
        unit=validated.get("unit", "units"),
        reorder_threshold=validated.get("reorder_threshold", 0),
    )


@transaction.atomic
def submit_requisition(actor, validated: dict) -> Requisition:
    """Create a requisition and its lines only when every item id exists."""
    lines = validated["items"]
    item_ids = [line["item_id"] for line in lines]
    found = {item.pk for item in InventoryItem.objects.filter(pk__in=item_ids)}
    if len(found) != len(set(item_ids)):
        raise DomainError(UNKNOWN_ITEM_MESSAGE, code="invalid_requisition_item")
    # `originator` is a local projection of the IAM principal. A staff member who
    # has never been a patient has no row yet; project them from the session so
    # the FK cannot turn a valid requisition into an IntegrityError 500.
    originator_id = getattr(actor, "user_id", None)
    if originator_id is not None:
        Patient.objects.get_or_create(
            user_id=originator_id,
            defaults={
                "display_name": (getattr(actor, "display_name", "") or
                                 f"User {originator_id}")[:150],
                "kind": (getattr(actor, "kind", "") or "staff")[:16],
            },
        )
    requisition = Requisition.objects.create(
        originator_id=originator_id,
        user_id=originator_id,
        state="pending_approval",
    )
    for line in lines:
        RequisitionItem.objects.create(
            requisition=requisition, item_id=line["item_id"],
            quantity=line["quantity"],
        )
    audit.record(actor, "requisition.submit", "requisition", requisition.pk,
                 {"state": requisition.state})
    return requisition


def _lock_requisition(pk: int, action: str, expected_updated_at=None) -> Requisition:
    requisition = (Requisition.objects
                   .select_for_update().filter(pk=pk).first())
    if requisition is None:
        raise NotFoundError(REQ_NOT_FOUND, code="not_found")
    if expected_updated_at is not None and str(requisition.updated_at) != str(expected_updated_at):
        raise ConflictError(ALREADY_DONE_MESSAGE, code="conflict")
    if requisition.state != REQUISITION_EXPECTED[action]:
        raise NotFoundError(WAITING_MESSAGE, code="not_found")
    return requisition


@transaction.atomic
def decide_requisition(actor, pk: int, decision: str, note: str = "",
                       expected_updated_at=None) -> Requisition:
    requisition = _lock_requisition(pk, decision, expected_updated_at)
    requisition.state = next_requisition_state(requisition.state, decision)
    requisition.decided_by = getattr(actor, "user_id", None)
    requisition.decided_at = timezone.now()
    requisition.decision_note = note
    requisition.save()
    audit.record(actor,
                 "requisition.approve" if decision == "approve" else "requisition.reject",
                 "requisition", requisition.pk, {"state": requisition.state})
    notifications.requisition_notice(requisition, decision)
    return requisition


@transaction.atomic
def fulfill_requisition(actor, pk: int, expected_updated_at=None) -> Requisition:
    requisition = _lock_requisition(pk, "fulfill", expected_updated_at)
    requisition.state = next_requisition_state(requisition.state, "fulfill")
    requisition.save()
    audit.record(actor, "requisition.fulfill", "requisition", requisition.pk,
                 {"state": requisition.state})
    return requisition
