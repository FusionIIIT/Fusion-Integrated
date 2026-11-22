"""Report categories and the anonymisation applied to patient-derived counts (PHC-BR-12)."""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

CATEGORIES = ("demographics", "utilization", "inventory")

# A bucket this small could single a patient out, so it is reported as "<5".
SMALL_CELL = 5


class ReportParameterError(Exception):
    pass


@dataclass(frozen=True)
class ReportRequest:
    category: str
    start: date
    end: date


def validate_request(category: str, start: date, end: date) -> ReportRequest:
    if category not in CATEGORIES:
        raise ReportParameterError(
            f"Choose a report category: {', '.join(CATEGORIES)}.")
    if start > end:
        raise ReportParameterError("The start date must be on or before the end date.")
    return ReportRequest(category, start, end)


def suppress(count: int) -> int | str:
    return "<5" if 0 < count < SMALL_CELL else count


def anonymised_counts(labels: Iterable[str]) -> dict[str, int | str]:
    tally: dict[str, int] = {}
    for label in labels:
        tally[label] = tally.get(label, 0) + 1
    return {label: suppress(n) for label, n in sorted(tally.items())}
