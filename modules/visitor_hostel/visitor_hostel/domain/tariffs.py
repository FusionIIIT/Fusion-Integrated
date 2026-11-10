"""Tariff selection (BR-VH-019, BR-VH-023).

A tariff is effective-dated and never edited: a change is a new row with a
later `effective_from`. The applicable one is the latest that had started on
the date being billed, so history cannot move under an existing bill
(BR-VH-024 — bills also copy the rate onto their own lines).
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

CATEGORIES = ("A", "B", "C", "D")
SINGLE = "single"
DOUBLE = "double"
OCCUPANCIES = (SINGLE, DOUBLE)                     # BR-VH-013, BR-VH-014
SUITE = "suite"
NON_SUITE = "non_suite"
ROOM_TYPES = (SUITE, NON_SUITE)                    # BR-VH-015, BR-VH-016


class NoApplicableTariff(Exception):
    def __init__(self, key: str, on: date):
        super().__init__(
            f"No tariff for {key} was in effect on {on.isoformat()}. Record one "
            f"with an effective-from date on or before it.")
        self.key, self.on = key, on


@dataclass(frozen=True)
class TariffRow:
    id: int
    key: str
    rate: Decimal
    effective_from: date


def room_key(category: str, occupancy: str) -> str:
    if category not in CATEGORIES:
        raise ValueError(f"Visitor category must be one of {', '.join(CATEGORIES)}.")
    if occupancy not in OCCUPANCIES:
        raise ValueError("Occupancy must be single or double.")
    return f"room:{category}:{occupancy}"


def meal_key(item: str) -> str:
    return f"meal:{item}"


def select(rows: Iterable[TariffRow], *, key: str, on: date) -> TariffRow:
    candidates = [r for r in rows if r.key == key and r.effective_from <= on]
    if not candidates:
        raise NoApplicableTariff(key, on)
    return max(candidates, key=lambda r: (r.effective_from, r.id))
