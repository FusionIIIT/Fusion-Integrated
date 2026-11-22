"""PSM public contract surface for other Fusion modules. Plural by signature."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal

from modules.psm.models.indent import Indent
from modules.psm.models.inventory import StockItem
from modules.psm.models.vendor import Vendor


@dataclass(frozen=True)
class IndentDTO:
    indent_id: int
    indent_number: str
    user_id: int
    status: str
    estimated_total: Decimal


@dataclass(frozen=True)
class StockLevelDTO:
    item_code: str
    quantity_on_hand: int
    quantity_reserved: int
    available_quantity: int


@dataclass(frozen=True)
class VendorStatusDTO:
    vendor_id: int
    vendor_code: str
    name: str
    status: str
    is_verified: bool


def get_indents(indent_ids: Sequence[int]) -> dict[int, IndentDTO]:
    """Plural batch fetch for indents by ID."""
    ids = {int(i) for i in indent_ids if i is not None}
    if not ids:
        return {}

    indents = Indent.objects.filter(pk__in=ids)
    return {
        ind.id: IndentDTO(
            indent_id=ind.id,
            indent_number=ind.indent_number,
            user_id=ind.user_id,
            status=ind.status,
            estimated_total=ind.estimated_total,
        )
        for ind in indents
    }


def get_stock_levels(item_codes: Sequence[str]) -> dict[str, StockLevelDTO]:
    """Plural inventory availability query by item code."""
    codes = {str(c).strip() for c in item_codes if c}
    if not codes:
        return {}

    stocks = StockItem.objects.filter(
        item_master__item_code__in=codes,
    ).select_related("item_master")
    return {
        s.item_master.item_code: StockLevelDTO(
            item_code=s.item_master.item_code,
            quantity_on_hand=s.quantity_on_hand,
            quantity_reserved=s.quantity_reserved,
            available_quantity=s.available_quantity,
        )
        for s in stocks
    }


def get_vendor_statuses(vendor_ids: Sequence[int]) -> dict[int, VendorStatusDTO]:
    """Plural vendor vetting status verification."""
    ids = {int(v) for v in vendor_ids if v is not None}
    if not ids:
        return {}

    vendors = Vendor.objects.filter(pk__in=ids)
    return {
        v.id: VendorStatusDTO(
            vendor_id=v.id,
            vendor_code=v.vendor_code,
            name=v.name,
            status=v.status,
            is_verified=(v.status == "VERIFIED"),
        )
        for v in vendors
    }
