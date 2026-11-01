from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.visitors_hostel.models import (
    InventoryChange, InventoryItem, OperationalRoleAssignment,
    ReplenishmentRequest)
from modules.visitors_hostel.services import notifications


def _caretaker_user_id():
    return OperationalRoleAssignment.objects.filter(
        role="caretaker", ends_at__isnull=True).values_list("user_id", flat=True).first()


@transaction.atomic
def change_quantity(*, item_id, actor, delta, note=""):
    if not actor.has_permission("visitor_hostel.inventory.manage"):
        raise PermissionDeniedError()
    item = InventoryItem.objects.select_for_update().filter(pk=item_id, active=True).first()
    if item is None:
        raise NotFoundError("No such inventory item.")
    previous = item.current_quantity
    quantity = previous + Decimal(str(delta))
    if quantity < 0:
        raise ConflictError("Inventory quantity cannot become negative.",
                            code="negative_inventory")
    item.current_quantity = quantity
    item.save(update_fields=["current_quantity", "updated_at"])
    InventoryChange.objects.create(
        item=item, quantity_delta=delta, quantity_after=quantity,
        note=note, actor_user_id=actor.user_id)
    caretaker = _caretaker_user_id()
    if previous >= item.minimum_threshold and quantity < item.minimum_threshold and caretaker:
        notifications.enqueue(
            topic="inventory.threshold",
            dedupe_key=f"inventory:{item.pk}:below:{quantity}:{item.updated_at.isoformat()}",
            subject=f"VH inventory below threshold: {item.name}",
            body=(f"{item.name} is at {quantity} {item.unit}; minimum is "
                  f"{item.minimum_threshold} {item.unit}."),
            user_id=caretaker,
            payload={"item_id": item.pk, "quantity": str(quantity)})
    return item


def create_item(*, actor, name, current_quantity, minimum_threshold, unit):
    if not actor.has_permission("visitor_hostel.inventory.manage"):
        raise PermissionDeniedError()
    quantity = Decimal(str(current_quantity))
    threshold = Decimal(str(minimum_threshold))
    if quantity < 0 or threshold < 0 or not unit:
        raise ConflictError("Inventory quantity, threshold, and unit are required.",
                            code="invalid_inventory_item")
    item = InventoryItem.objects.create(name=name, current_quantity=quantity,
                                        minimum_threshold=threshold, unit=unit)
    caretaker = _caretaker_user_id()
    if quantity < threshold and caretaker:
        notifications.enqueue(
            topic="inventory.threshold", dedupe_key=f"inventory:{item.pk}:initial-low",
            subject=f"VH inventory below threshold: {item.name}",
            body=(f"{item.name} is at {quantity} {item.unit}; minimum is "
                  f"{threshold} {item.unit}."),
            user_id=caretaker,
            payload={"item_id": item.pk, "quantity": str(quantity)})
    return item


def create_replenishment_request(*, item_id, actor, quantity):
    if not actor.has_permission("visitor_hostel.inventory.manage"):
        raise PermissionDeniedError()
    item = InventoryItem.objects.filter(pk=item_id, active=True).first()
    if item is None:
        raise NotFoundError("No such inventory item.")
    if Decimal(str(quantity)) <= 0:
        raise ConflictError("Requested quantity must be positive.",
                            code="invalid_quantity")
    return ReplenishmentRequest.objects.create(
        item=item, requested_quantity=quantity, requested_by_user_id=actor.user_id)


@transaction.atomic
def review_replenishment(*, request_id, actor, approve, note=""):
    if not actor.has_permission("visitor_hostel.inventory.approve"):
        raise PermissionDeniedError()
    request = ReplenishmentRequest.objects.select_for_update().filter(
        pk=request_id, status="pending").first()
    if request is None:
        raise NotFoundError("No pending replenishment request.")
    request.status = "approved" if approve else "rejected"
    request.reviewed_by_user_id = actor.user_id
    request.reviewed_at = timezone.now()
    request.review_note = note
    request.save(update_fields=["status", "reviewed_by_user_id", "reviewed_at",
                                "review_note", "updated_at"])
    return request
