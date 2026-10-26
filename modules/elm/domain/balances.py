"""Balance arithmetic and the year-end plan (BR-EL-002..009, WF-EL-07)."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from modules.elm.domain import leave_types as lt
from modules.elm.domain.errors import RuleViolation

ZERO = Decimal(0)


def remaining(entitled: Decimal, carried_in: Decimal, used: Decimal,
              lapsed: Decimal) -> Decimal:
    return entitled + carried_in - used - lapsed


def check_balance(requested: Decimal, available: Decimal) -> None:
    if requested > available:
        raise RuleViolation(
            f"Requested {requested} day(s) but only {available} remain.", "BR-EL-002")


def check_scl_ceiling(requested: Decimal, already_taken: Decimal) -> None:
    if already_taken + requested > lt.ANNUAL_CREDIT[lt.STAFF][lt.SCL]:
        raise RuleViolation("SCL cannot exceed 15 days in a year.", "BR-EL-004")


@dataclass(frozen=True)
class YearEndPlan:
    lapse: Decimal = ZERO
    carry_forward: Decimal = ZERO
    #: EL credited to next year, from converting VL.
    el_credit: Decimal = ZERO


def plan_year_end(leave_type: str, left: Decimal) -> YearEndPlan:
    left = max(left, ZERO)
    if leave_type in lt.LAPSES_AT_YEAR_END:
        return YearEndPlan(lapse=left)
    if leave_type in lt.CARRIES_FORWARD:
        return YearEndPlan(carry_forward=left)
    if leave_type == lt.VL:
        return YearEndPlan(lapse=left, el_credit=left / lt.VL_PER_EL)
    return YearEndPlan()
