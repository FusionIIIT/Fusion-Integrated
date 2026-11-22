# Inventory and replenishment services for VHMS.
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.vh.models.inventory import InventoryItem, InventoryReplenishment
from modules.vh.services.notifications import notify_inventory_threshold


@transaction.atomic
def update_inventory_stock(
    item_id: int,
    quantity_delta: int,
    principal,
) -> InventoryItem:
    # CFR-VH-012, BR-VH-041, BR-VH-043: Updates inventory item and detects threshold breaches.
    try:
        item = InventoryItem.objects.select_for_update().get(id=item_id)
    except InventoryItem.DoesNotExist:
        raise NotFoundError(f"Inventory item {item_id} not found.") from None

    new_qty = item.current_quantity + quantity_delta
    if new_qty < 0:
        raise BadRequestError(f"Cannot reduce quantity below 0 (current: {item.current_quantity}).")

    item.current_quantity = new_qty
    was_below = item.is_threshold_alert
    is_below = item.current_quantity < item.minimum_threshold
    item.is_threshold_alert = is_below
    item.save()

    if is_below and not was_below:
        notify_inventory_threshold(item)

    return item


@transaction.atomic
def save_inventory_item(data: dict, principal) -> InventoryItem:
    # Creates or updates an inventory item with thresholds.
    item_id = data.get("id")
    name = data.get("item_name", "").strip()
    category = data.get("category", "consumables").strip().lower()
    qty = int(data.get("current_quantity", 0))
    threshold = int(data.get("minimum_threshold", 10))
    unit = data.get("unit", "pieces").strip()

    if not name:
        raise BadRequestError("Inventory item name is required.")

    if item_id:
        try:
            item = InventoryItem.objects.select_for_update().get(id=item_id)
        except InventoryItem.DoesNotExist:
            raise NotFoundError(f"Inventory item {item_id} not found.") from None
        item.item_name = name
        item.category = category
        item.current_quantity = qty
        item.minimum_threshold = threshold
        item.unit = unit
    else:
        item = InventoryItem(
            item_name=name,
            category=category,
            current_quantity=qty,
            minimum_threshold=threshold,
            unit=unit,
        )

    item.is_threshold_alert = item.current_quantity < item.minimum_threshold
    item.save()

    if item.is_threshold_alert:
        notify_inventory_threshold(item)

    return item


@transaction.atomic
def request_replenishment(
    item_id: int, requested_quantity: int, remarks: str, principal
) -> InventoryReplenishment:
    # Caretaker records inventory replenishment requirement.
    try:
        item = InventoryItem.objects.get(id=item_id)
    except InventoryItem.DoesNotExist:
        raise NotFoundError(f"Inventory item {item_id} not found.") from None

    if requested_quantity < 1:
        raise BadRequestError("Replenishment quantity must be at least 1.")

    caretaker_id = getattr(principal, "user_id", 0)
    return InventoryReplenishment.objects.create(
        item=item,
        requested_quantity=requested_quantity,
        status="pending",
        requested_by=caretaker_id,
        remarks=remarks.strip(),
    )


@transaction.atomic
def approve_replenishment(
    replenishment_id: int, decision: str, remarks: str, principal
) -> InventoryReplenishment:
    # CFR-VH-013, UC-VH-015: VH In-Charge reviews and approves/rejects replenishment requirement.
    try:
        req = InventoryReplenishment.objects.select_for_update().get(id=replenishment_id)
    except InventoryReplenishment.DoesNotExist:
        raise NotFoundError(f"Replenishment request {replenishment_id} not found.") from None

    if req.status != "pending":
        raise ConflictError(f"Replenishment request is already '{req.status}'.")

    dec = decision.strip().lower()
    if dec not in {"approved", "rejected"}:
        raise BadRequestError("Decision must be 'approved' or 'rejected'.")

    incharge_id = getattr(principal, "user_id", 0)
    req.status = dec
    req.approved_by = incharge_id
    req.approved_at = timezone.now()
    if remarks:
        req.remarks = f"{req.remarks} | Decision notes: {remarks.strip()}"
    req.save()

    if dec == "approved":
        item = InventoryItem.objects.select_for_update().get(id=req.item_id)
        item.current_quantity += req.requested_quantity
        item.is_threshold_alert = item.current_quantity < item.minimum_threshold
        item.save()

    return req


def evaluate_all_inventory_thresholds() -> int:
    # Periodic evaluation of items falling below thresholds.
    count = 0
    items = InventoryItem.objects.filter(
        current_quantity__lt=F("minimum_threshold"), is_threshold_alert=False
    )
    for item in items:
        item.is_threshold_alert = True
        item.save()
        notify_inventory_threshold(item)
        count += 1
    return count
