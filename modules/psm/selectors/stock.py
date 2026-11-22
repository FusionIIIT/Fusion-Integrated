"""
Stock Item & Transfer Read Selectors.
"""

from typing import Any, Optional
from django.db.models import QuerySet
from modules.psm.models import StockItem, StockTransfer


def get_allocable_stock(stock_item_id: Any) -> int:
    """Calculate allocable stock for a stock item:
    Allocable = central_stock + department_stock - reserved_stock
    """
    try:
        item = StockItem.objects.filter(id=int(stock_item_id)).first()
        if not item:
            return 0
        allocable = (item.central_stock + item.department_stock) - item.reserved_stock
        return max(0, allocable)
    except Exception:
        return 0


def list_stock_transfers(principal: Any = None) -> QuerySet[StockTransfer]:
    """List stock transfers ordered by newest first."""
    return StockTransfer.objects.all().order_by("-created_at")


def list_stock_items(department: Optional[str] = None) -> QuerySet[StockItem]:
    """List stock items, optionally by department."""
    qs = StockItem.objects.all().order_by("name")
    if department:
        qs = qs.filter(department=department)
    return qs
