"""Post-grant maintenance: when tracking applies and when each fee falls due."""
from __future__ import annotations

import calendar
from datetime import date

from modules.pms.domain import state_machine as sm


def may_track(status: str) -> bool:
    """BR-PMS-059."""
    return status == sm.GRANTED


def add_months(day: date, months: int) -> date:
    month_index = day.month - 1 + months
    year, month = day.year + month_index // 12, month_index % 12 + 1
    return date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


def schedule(grant_date: date, jurisdiction: str,
             rules: dict[str, tuple[int, ...]]) -> tuple[date, ...]:
    """BR-PMS-060: due dates from the grant date where a rule exists, else none at all."""
    return tuple(add_months(grant_date, m) for m in rules.get(jurisdiction, ()))


def next_due(grant_date: date, jurisdiction: str, rules: dict[str, tuple[int, ...]],
             after: date) -> date | None:
    return next((d for d in schedule(grant_date, jurisdiction, rules) if d > after), None)


def decision_open(due_on: date, today: date) -> bool:
    """BR-PMS-061: the renewal decision is taken on or before the deadline."""
    return today <= due_on
