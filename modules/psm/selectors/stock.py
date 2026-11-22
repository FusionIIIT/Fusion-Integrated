# Constant-query stock availability aggregation (PSM-UC-007, PSM-UC-017, BR-PSM-013).
from __future__ import annotations

from django.db.models import Sum

from modules.psm.domain.stock_rules import StockBalance, allocable_quantity
from modules.psm.models import StockItem, StockLedgerEntry, StockLocation, StockReservation
from modules.psm.selectors import scoping


def stock_balances_for_item(item_id: int) -> list[StockBalance]:
    """Compute on-hand, reserved, and allocable stock across all locations in 3 queries."""
    locations = list(StockLocation.objects.all())
    ledger_sums = {
        row["location_id"]: row["total"] or 0
        for row in StockLedgerEntry.objects.filter(item_id=item_id)
        .values("location_id")
        .annotate(total=Sum("quantity_delta"))
    }
    reserved_sums = {
        row["location_id"]: row["total"] or 0
        for row in StockReservation.objects.filter(item_id=item_id, status="active")
        .values("location_id")
        .annotate(total=Sum("quantity"))
    }
    return [
        StockBalance(
            location_id=loc.pk,
            location_code=loc.code,
            department=loc.department,
            is_central=loc.is_central,
            on_hand=ledger_sums.get(loc.pk, 0),
            reserved=reserved_sums.get(loc.pk, 0),
        )
        for loc in locations
    ]


def _aggregate_maps(item_ids: list[int], loc_ids: list[int]) -> tuple[dict, dict]:
    """Fetch summed ledger on-hand and active reservation quantities in two queries."""
    ledger_map = {
        (r["item_id"], r["location_id"]): r["total"] or 0
        for r in StockLedgerEntry.objects.filter(item_id__in=item_ids, location_id__in=loc_ids)
        .values("item_id", "location_id")
        .annotate(total=Sum("quantity_delta"))
    }
    res_map = {
        (r["item_id"], r["location_id"]): r["total"] or 0
        for r in StockReservation.objects.filter(
            item_id__in=item_ids, location_id__in=loc_ids, status="active"
        )
        .values("item_id", "location_id")
        .annotate(total=Sum("quantity"))
    }
    return ledger_map, res_map


def availability_rows(
    actor, *, item_id: int | None = None, location_id: int | None = None
) -> list[dict]:
    """Return scoped on-hand, reserved, and allocable stock rows in constant queries."""
    locs = list(scoping.stock_locations_for(actor))
    if location_id is not None:
        locs = [loc for loc in locs if loc.pk == location_id]
    if not locs:
        return []
    items_qs = StockItem.objects.filter(is_active=True)
    if item_id is not None:
        items_qs = items_qs.filter(pk=item_id)
    items = list(items_qs)
    if not items:
        return []
    ledger_map, res_map = _aggregate_maps([it.pk for it in items], [loc.pk for loc in locs])
    rows: list[dict] = []
    for it in items:
        for loc in locs:
            on_hand = ledger_map.get((it.pk, loc.pk), 0)
            reserved = res_map.get((it.pk, loc.pk), 0)
            if on_hand == 0 and reserved == 0 and item_id is None:
                continue
            rows.append(
                {
                    "item_id": it.pk,
                    "sku": it.sku,
                    "item_name": it.name,
                    "unit": it.unit,
                    "location_id": loc.pk,
                    "location_code": loc.code,
                    "location_name": loc.name,
                    "department": loc.department,
                    "is_central": loc.is_central,
                    "on_hand": on_hand,
                    "reserved": reserved,
                    "allocable": allocable_quantity(on_hand, reserved),
                }
            )
    return rows
