# Pure-Python stock availability and reservation calculations (BR-PSM-003, BR-PSM-013, BR-PSM-027).
from __future__ import annotations

from dataclasses import dataclass

from modules.psm.domain.errors import ConflictRuleError, ValidationRuleError


@dataclass(frozen=True)
class StockBalance:
    location_id: int
    location_code: str
    department: str
    is_central: bool
    on_hand: int
    reserved: int

    @property
    def allocable(self) -> int:
        return max(0, self.on_hand - self.reserved)


def allocable_quantity(on_hand: int, reserved: int) -> int:
    """Compute allocable stock excluding active reservations (BR-PSM-013)."""
    return max(0, on_hand - reserved)


def select_allocation_location(
    balances: list[StockBalance], department: str, required_qty: int
) -> StockBalance | None:
    """Check departmental stock first, then central stock, for BR-PSM-003."""
    if required_qty <= 0:
        raise ValidationRuleError(
            "Requested quantity must be greater than zero.", code="invalid_quantity"
        )
    dept_key = (department or "").strip().lower()
    dept_matches = [
        b
        for b in balances
        if not b.is_central
        and b.department.strip().lower() == dept_key
        and b.allocable >= required_qty
    ]
    if dept_matches:
        return sorted(dept_matches, key=lambda b: b.allocable, reverse=True)[0]
    central_matches = [b for b in balances if b.is_central and b.allocable >= required_qty]
    if central_matches:
        return sorted(central_matches, key=lambda b: b.allocable, reverse=True)[0]
    return None


def ensure_adjustment_non_negative(on_hand: int, reserved: int, delta: int) -> None:
    """Refuse an adjustment that would drop on-hand stock below active reservations."""
    if delta == 0:
        raise ValidationRuleError(
            "Enter a non-zero quantity delta for a stock adjustment.", code="zero_adjustment"
        )
    if on_hand + delta < reserved:
        raise ConflictRuleError(
            f"Adjustment leaves on-hand ({on_hand + delta}) below reserved ({reserved}).",
            code="stock_below_reserved",
        )
