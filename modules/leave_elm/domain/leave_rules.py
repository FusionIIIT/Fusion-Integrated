"""Baseline entitlement and carry-forward rules for Employee Leave Management."""

from decimal import Decimal
from typing import Optional

LEAVE_CATEGORIES = ("CL", "RH", "SCL", "EL", "COL", "VL")

ANNUAL_ENTITLEMENTS = {
    "CL": Decimal("8"),
    "RH": Decimal("2"),
    "SCL": Decimal("15"),
    "EL": Decimal("30"),
    "COL": Decimal("20"),
    "VL": Decimal("60"),
}

CARRY_FORWARD_CATEGORIES = frozenset({"EL", "COL"})
NON_CARRY_FORWARD_CATEGORIES = frozenset({"CL", "RH", "SCL", "VL"})


def annual_entitlement(
    category: str,
    *,
    is_faculty: bool = False,
    col_eligible: bool = True,
) -> Optional[Decimal]:
    """Return the baseline annual entitlement, or None if not applicable."""
    category = category.upper()

    if category not in LEAVE_CATEGORIES:
        raise ValueError(f"Unsupported leave category: {category}")

    if category == "EL" and is_faculty:
        # Faculty EL may be credited through VL conversion.
        # The baseline does not specify a direct annual faculty EL grant.
        return None

    if category == "VL" and not is_faculty:
        return None

    if category == "COL" and not col_eligible:
        return None

    return ANNUAL_ENTITLEMENTS[category]


def carries_forward(category: str) -> bool:
    """Return whether unused leave of this category carries forward."""
    category = category.upper()

    if category not in LEAVE_CATEGORIES:
        raise ValueError(f"Unsupported leave category: {category}")

    return category in CARRY_FORWARD_CATEGORIES


def convert_unused_vl_to_el(unused_vl: Decimal) -> Decimal:
    """Convert unused faculty VL to EL at the specified 2:1 ratio."""
    unused_vl = Decimal(str(unused_vl))

    if unused_vl < 0:
        raise ValueError("Unused VL cannot be negative")

    return unused_vl / Decimal("2")
