"""Effective holiday / RH / vacation calendar (BR-EL-031, BR-EL-003, BR-EL-006)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class CalendarWindow:
    kind: str  # closed | rh | vacation
    start: date
    end: date


@dataclass(frozen=True)
class PublishedCalendar:
    closed: frozenset[date]
    restricted: frozenset[date]
    vacations: tuple[tuple[date, date], ...]

    def is_closed(self, d: date) -> bool:
        return d in self.closed or d.weekday() >= 5

    def is_restricted_holiday(self, d: date) -> bool:
        return d in self.restricted

    def in_vacation(self, start: date, end: date) -> bool:
        for vs, ve in self.vacations:
            if start >= vs and end <= ve:
                return True
        return False


def empty_calendar() -> PublishedCalendar:
    return PublishedCalendar(frozenset(), frozenset(), ())
