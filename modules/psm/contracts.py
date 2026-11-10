"""
PSM Inter-Module Public Surface Contracts.
CI Rule Enforced: All cross-module contract getters MUST BE PLURAL.
"""

from typing import Any
from modules.psm.models import Indent, Vendor, StockItem


def get_indents(indent_ids: list[int]) -> list[dict[str, Any]]:
    """Retrieve multiple indents by primary key IDs for external consumers."""
    if not indent_ids:
        return []

    clean_ids = [int(i) for i in indent_ids if i is not None]
    indents = Indent.objects.filter(id__in=clean_ids)
    return [
        {
            "id": ind.id,
            "indent_id": ind.indent_id,
            "requestor_id": ind.requestor_id,
            "item_details": ind.item_details,
            "quantity": ind.quantity,
            "estimated_cost": str(ind.estimated_cost),
            "status": ind.status,
            "priority": ind.priority,
            "is_duplicate": ind.is_duplicate,
            "created_at": ind.created_at.isoformat() if ind.created_at else None,
        }
        for ind in indents
    ]


def get_vendors(vendor_ids: list[int]) -> list[dict[str, Any]]:
    """Retrieve multiple vendors by primary key IDs."""
    if not vendor_ids:
        return []

    clean_ids = [int(v) for v in vendor_ids if v is not None]
    vendors = Vendor.objects.filter(id__in=clean_ids)
    return [
        {
            "id": v.id,
            "name": v.name,
            "gst_number": v.gst_number,
            "is_verified": v.is_verified,
        }
        for v in vendors
    ]


def get_stock_items(item_codes: list[str]) -> list[dict[str, Any]]:
    """Retrieve multiple stock items by item codes."""
    if not item_codes:
        return []

    clean_codes = [str(c).strip() for c in item_codes if c]
    items = StockItem.objects.filter(item_code__in=clean_codes)
    return [
        {
            "id": item.id,
            "item_code": item.item_code,
            "name": item.name,
            "department": item.department,
            "central_stock": item.central_stock,
            "department_stock": item.department_stock,
            "reserved_stock": item.reserved_stock,
            "allocable_stock": max(
                0, (item.central_stock + item.department_stock) - item.reserved_stock
            ),
        }
        for item in items
    ]
