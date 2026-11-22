from django.db.models import Sum, Value
from django.db.models.functions import Coalesce

from modules.phc.models import InventoryItem, InventoryMovement, LowStockAlert


def items_with_stock():
    return InventoryItem.objects.annotate(
        stock_quantity=Coalesce(Sum("movements__quantity_delta"), Value(0))
    ).order_by("name", "id")


def movements_for_item(item_id: int):
    return InventoryMovement.objects.filter(item_id=item_id).order_by(
        "-created_at", "-id")


def low_stock_alerts():
    return LowStockAlert.objects.select_related("item", "movement").order_by(
        "-created_at", "-id")
