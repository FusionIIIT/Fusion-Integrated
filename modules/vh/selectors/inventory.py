# Inventory query selectors for VHMS.

from django.db.models import QuerySet

from modules.vh.models.inventory import InventoryItem, InventoryReplenishment


def list_inventory_items(category: str | None = None) -> QuerySet[InventoryItem]:
    # Returns inventory items with optional category filtering.
    qs = InventoryItem.objects.all().order_by("category", "item_name")
    if category:
        qs = qs.filter(category=category.lower())
    return qs


def list_replenishment_requests(status: str | None = None) -> QuerySet[InventoryReplenishment]:
    # Returns inventory replenishment requests.
    qs = InventoryReplenishment.objects.all().select_related("item").order_by("-created_at")
    if status:
        qs = qs.filter(status=status.lower())
    return qs
