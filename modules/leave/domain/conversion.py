"""VL-to-EL year-end conversion (BR-EL-007, BR-EL-008).

Unused faculty VL converts to EL at 2 VL : 1 EL, fractional conversion
included, and VL itself does not carry forward. The credited EL carries
forward and is available to the faculty member afterwards (BR-EL-008).
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

#: BR-EL-007 - two days of unused VL buy one day of EL.
VL_PER_EL = Decimal("2")


def vl_to_el(unused_vl: Decimal) -> Decimal:
    """EL credited for an unused VL balance; the fraction is retained."""
    if unused_vl < 0:
        raise ValueError("unused VL cannot be negative")
    return unused_vl / VL_PER_EL


@dataclass(frozen=True)
class Conversion:
    vl_surrendered: Decimal
    el_credited: Decimal

    @property
    def vl_carried(self) -> Decimal:
        """BR-EL-007 - VL never carries forward as VL."""
        return Decimal("0")


def convert(unused_vl: Decimal) -> Conversion:
    """BR-EL-007 - the year-end conversion of a faculty VL balance."""
    return Conversion(vl_surrendered=unused_vl, el_credited=vl_to_el(unused_vl))
