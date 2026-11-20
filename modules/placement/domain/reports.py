"""Report arithmetic: rates, salary bands and season trends (PC-AFR-033..036)."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

#: Upper bounds in LPA; the last band is open-ended.
BAND_EDGES = (Decimal(5), Decimal(10), Decimal(15), Decimal(20), Decimal(30))


@dataclass(frozen=True)
class SeasonTrend:
    season: str
    registered: int
    placed: int
    placement_rate: float | None
    companies_participated: int


def placement_rate(placed: int, registered: int) -> float | None:
    return round(placed * 100 / registered, 1) if registered else None


def band_label(index: int) -> str:
    if index == len(BAND_EDGES):
        return f"{BAND_EDGES[-1]}+ LPA"
    low = BAND_EDGES[index - 1] if index else Decimal(0)
    return f"{low}-{BAND_EDGES[index]} LPA"


def salary_distribution(ctcs: list[Decimal]) -> list[dict]:
    """Count packages per band; a package on an edge falls in the higher band."""
    counts = [0] * (len(BAND_EDGES) + 1)
    for ctc in ctcs:
        counts[sum(1 for edge in BAND_EDGES if ctc >= edge)] += 1
    return [{"band": band_label(i), "placed": n} for i, n in enumerate(counts)]


def season_trends(seasons: list[str], registered: dict[str, int],
                  placed: dict[str, int], companies: dict[str, int]) -> list[SeasonTrend]:
    """One row per season, oldest first, so a trend reads left to right."""
    return [
        SeasonTrend(season=s, registered=registered.get(s, 0), placed=placed.get(s, 0),
                    placement_rate=placement_rate(placed.get(s, 0), registered.get(s, 0)),
                    companies_participated=companies.get(s, 0))
        for s in sorted(seasons)
    ]
