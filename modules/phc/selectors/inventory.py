"""Inventory and requisition selectors (CFR-PHC-006, CFR-PHC-007)."""
from modules.phc.models.inventory import (
    InventoryItem,
    InventoryStockAdjustment,
    ProcurementRequisition,
)


def list_inventory_items(category: str | None = None) -> list[InventoryItem]:
    qs = InventoryItem.objects.all()
    if category:
        qs = qs.filter(category=category)
    return list(qs.order_by("name"))


def get_inventory_item(item_id: int) -> InventoryItem:
    return InventoryItem.objects.prefetch_related("adjustments").get(id=item_id)


def list_stock_adjustments(item_id: int | None = None) -> list[InventoryStockAdjustment]:
    qs = InventoryStockAdjustment.objects.select_related("item").all()
    if item_id:
        qs = qs.filter(item_id=item_id)
    return list(qs.order_by("-created_at")[:100])


def list_procurement_requisitions(status: str | None = None) -> list[ProcurementRequisition]:
    qs = ProcurementRequisition.objects.prefetch_related("items", "items__item").all()
    if status:
        qs = qs.filter(status=status)
    return list(qs.order_by("-created_at"))


def get_procurement_requisition(requisition_id: int) -> ProcurementRequisition:
    return ProcurementRequisition.objects.prefetch_related("items", "items__item").get(id=requisition_id)
