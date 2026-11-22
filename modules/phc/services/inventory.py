"""Inventory items, stock adjustments and low-stock alerts (PHC-UC-09)."""
from __future__ import annotations

from decimal import Decimal

from django.db import IntegrityError, transaction

from core.api.exceptions import ConflictError, DomainError, NotFoundError
from modules.phc.domain import rules
from modules.phc.models import InventoryItem, LowStockAlert, StockAdjustment
from modules.phc.services import trail


@transaction.atomic
def create_item(*, actor, name: str, unit: str, stock_level: Decimal,
                reorder_threshold: Decimal) -> InventoryItem:
    if stock_level < 0 or reorder_threshold < 0:
        raise DomainError("Stock level and reorder threshold cannot be negative.",
                          code="negative_quantity")
    try:
        with transaction.atomic():
            item = InventoryItem.objects.create(name=name, unit=unit, stock_level=stock_level,
                                                reorder_threshold=reorder_threshold)
    except IntegrityError as exc:
        raise ConflictError(f"An item named {name} already exists.",
                            code="duplicate_item") from exc
    # PHC-BR-09
    trail.audit(actor_user_id=actor.user_id, resource_type="inventory_item",
                resource_id=item.pk, action="create",
                details={"stock_level": str(stock_level),
                         "reorder_threshold": str(reorder_threshold)})
    return item


@transaction.atomic
def adjust_stock(*, actor, item_id: int, delta: Decimal, reason: str) -> StockAdjustment:
    item = InventoryItem.objects.select_for_update().filter(pk=item_id).first()
    if item is None:
        raise NotFoundError("That inventory item does not exist.")
    try:
        level = rules.apply_stock_change(item.stock_level, delta)
    except rules.RuleViolation as exc:
        raise DomainError(exc.message, code=exc.code) from exc
    item.stock_level = level
    item.save(update_fields=("stock_level", "updated_at"))
    adjustment = StockAdjustment.objects.create(item=item, delta=delta, level_after=level,
                                                reason=reason,
                                                adjusted_by_user_id=actor.user_id)
    # PHC-BR-09
    trail.audit(actor_user_id=actor.user_id, resource_type="inventory_item",
                resource_id=item.pk, action="adjust",
                details={"delta": str(delta), "level_after": str(level)})
    # PHC-BR-07
    if rules.is_low_stock(level, item.reorder_threshold):
        LowStockAlert.objects.create(item=item, adjustment=adjustment, level=level,
                                     threshold=item.reorder_threshold)
    return adjustment
