"""Leave entitlement, quota, and year-end conversion rules (pure Python).

Implements BR-EL-002 through BR-EL-009.
"""
from __future__ import annotations

from decimal import Decimal

STANDARD_QUOTAS: dict[str, dict[str, Decimal]] = {
    "faculty": {
        "CL": Decimal("8.0"),
        "RH": Decimal("2.0"),
        "SCL": Decimal("15.0"),
        "EL": Decimal("0.0"),     # Faculty receive EL via VL conversion
        "COL": Decimal("20.0"),
        "VL": Decimal("60.0"),
    },
    "staff": {
        "CL": Decimal("8.0"),
        "RH": Decimal("2.0"),
        "SCL": Decimal("15.0"),
        "EL": Decimal("30.0"),    # Non-faculty receive 30 EL directly
        "COL": Decimal("20.0"),
        "VL": Decimal("0.0"),
    },
}

CATEGORIES_THAT_LAPSE = frozenset({"CL", "RH", "SCL"})
CATEGORIES_THAT_CARRY_FORWARD = frozenset({"EL", "COL"})


def get_annual_quota(cadre: str, leave_type: str) -> Decimal:
    """Return the annual quota for a cadre and leave category."""
    norm_cadre = "faculty" if cadre == "faculty" else "staff"
    return STANDARD_QUOTAS.get(norm_cadre, {}).get(leave_type, Decimal("0.0"))


def calculate_vl_to_el_conversion(unused_vl: Decimal) -> Decimal:
    """Convert unused faculty VL to EL at 2 VL : 1 EL ratio (BR-EL-007).

    Fractional conversion is preserved (e.g. 15 VL -> 7.5 EL).
    """
    if unused_vl <= Decimal("0.0"):
        return Decimal("0.0")
    return unused_vl / Decimal("2.0")
