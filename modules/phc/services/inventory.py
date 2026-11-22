from django.db import IntegrityError, transaction
from django.db.models import Sum

from core.api.exceptions import ConflictError, NotFoundError
from modules.phc.domain.inventory import is_low_stock, stock_after
from modules.phc.models import InventoryItem, InventoryMovement, LowStockAlert
from modules.phc.services.common import audit


def stock_quantity(item_id: int) -> int:
    return InventoryMovement.objects.filter(item_id=item_id).aggregate(
        quantity=Sum("quantity_delta"))["quantity"] or 0


def create_item(*, name: str, unit: str, reorder_threshold: int) -> InventoryItem:
    try:
        with transaction.atomic():
            return InventoryItem.objects.create(
                name=name, unit=unit or "units", reorder_threshold=reorder_threshold)
    except IntegrityError as exc:
        raise ConflictError("Choose a name that is not already in the inventory.",
                            code="inventory_item_exists") from exc


def adjust_stock(*, item_id: int, quantity_delta: int, reason: str, actor_user_id: int):
    try:
        with transaction.atomic():
            item = InventoryItem.objects.select_for_update().get(pk=item_id, is_active=True)
            current = stock_quantity(item.pk)
            try:
                updated = stock_after(current, quantity_delta)
            except ValueError as exc:
                raise ConflictError(str(exc), code="stock_adjustment_invalid") from exc
            movement = InventoryMovement.objects.create(
                item=item, quantity_delta=quantity_delta, reason=reason,
                actor_user_id=actor_user_id)
            audit(actor_user_id=actor_user_id, action="inventory.stock_adjusted",
                  object_type="inventory_item", object_id=item.pk,
                  metadata={"quantity_delta": quantity_delta, "quantity_after": updated})
            if is_low_stock(updated, item.reorder_threshold):
                LowStockAlert.objects.create(
                    item=item, movement=movement, quantity_after=updated,
                    reorder_threshold=item.reorder_threshold)
            return item, updated, movement
    except InventoryItem.DoesNotExist as exc:
        raise NotFoundError("That active inventory item does not exist.",
                            code="inventory_item_not_found") from exc
