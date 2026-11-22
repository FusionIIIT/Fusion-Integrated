from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

CostBand = Literal["low", "mid", "high"]


@dataclass(frozen=True)
class CostBandResult:
    band: CostBand
    requires_committee: bool
    requires_director: bool
    bidding_allowed: bool


def classify_cost_band(total_cost: Decimal) -> CostBandResult:
    """Classifies repair estimate by monetary thresholds (BR-IWD-003)."""
    if total_cost < Decimal("25000"):
        return CostBandResult(
            band="low",
            requires_committee=False,
            requires_director=False,
            bidding_allowed=False,
        )
    if total_cost <= Decimal("250000"):
        return CostBandResult(
            band="mid",
            requires_committee=True,
            requires_director=False,
            bidding_allowed=False,
        )
    return CostBandResult(
        band="high",
        requires_committee=False,
        requires_director=True,
        bidding_allowed=True,
    )
