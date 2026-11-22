"""Year-end processing calculation (BR-EL-002, BR-EL-007, BR-EL-008, EL-UC-020)."""
from __future__ import annotations

from decimal import Decimal
from typing import Dict, Any


def compute_year_end_transition(
    cl: Decimal,
    rh: Decimal,
    scl: Decimal,
    el: Decimal,
    vl: Decimal,
    col: Decimal,
    is_faculty: bool,
) -> Dict[str, Any]:
    """Calculate lapsed, converted, and carried-forward values for year end.

    CL, RH, SCL lapse.
    Unused VL converts to EL at 2 VL : 1 EL (including fractional).
    VL itself does not carry forward.
    EL and COL carry forward.
    """
    vl_to_el_credit = (vl / Decimal("2.0")) if is_faculty else Decimal("0.0")

    carried_el = el + vl_to_el_credit
    carried_col = col

    return {
        "lapsed_cl": cl,
        "lapsed_rh": rh,
        "lapsed_scl": scl,
        "lapsed_vl": vl if not is_faculty else Decimal("0.0"),
        "converted_vl_to_el": vl_to_el_credit,
        "carried_el": carried_el,
        "carried_col": carried_col,
    }
