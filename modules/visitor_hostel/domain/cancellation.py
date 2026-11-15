"""The stated cancellation charge schedule (BR-VH-006..009).

    exactly 7 days before arrival     no charge                 BR-VH-007
    within 7 days, not same day       25% of one-day room rent  BR-VH-008
    same day, or a recorded no-show   50% of one-day room rent  BR-VH-009

The same-day case takes precedence over "within 7 days", as the workflow spec
says. More than 7 days out is not stated by the source; it is charged nothing
and tagged `beyond_schedule` so the decision is visible and queryable (see the
blueprint's open questions).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

TWO_PLACES = Decimal("0.01")


class NotBeforeArrival(Exception):
    """A cancellation request after the arrival date is not a pre-arrival one."""


@dataclass(frozen=True)
class ChargeCase:
    code: str
    percent: Decimal
    rule: str
    #: The source schedule does not state this case; the outcome needs a policy decision.
    needs_clarification: bool = False


SEVEN_DAYS = ChargeCase("seven_days", Decimal("0"), "BR-VH-007")
WITHIN_SEVEN_DAYS = ChargeCase("within_seven_days", Decimal("25"), "BR-VH-008")
SAME_DAY = ChargeCase("same_day", Decimal("50"), "BR-VH-009")
NO_SHOW = ChargeCase("no_show", Decimal("50"), "BR-VH-009")
BEYOND_SCHEDULE = ChargeCase("beyond_schedule", Decimal("0"), "BR-VH-006",
                             needs_clarification=True)

CASES = {c.code: c for c in (SEVEN_DAYS, WITHIN_SEVEN_DAYS, SAME_DAY, NO_SHOW,
                             BEYOND_SCHEDULE)}


def days_before(arrival: date, requested_on: date) -> int:
    return (arrival - requested_on).days


def case_for(arrival: date, requested_on: date) -> ChargeCase:
    """Which row of the schedule a cancellation on `requested_on` falls in."""
    days = days_before(arrival, requested_on)
    if days < 0:
        raise NotBeforeArrival(
            "The arrival date has passed, so this is no longer a pre-arrival "
            "cancellation.")
    if days == 0:
        return SAME_DAY
    if days < 7:
        return WITHIN_SEVEN_DAYS
    if days == 7:
        return SEVEN_DAYS
    return BEYOND_SCHEDULE


def charge(case: ChargeCase, one_day_rent: Decimal | None) -> Decimal:
    """Percent of one day's rent, to the paisa. Zero needs no rent at all."""
    if case.percent == 0:
        return Decimal("0.00")
    if one_day_rent is None:
        raise ValueError("A chargeable case needs the one-day room rent.")
    return (Decimal(one_day_rent) * case.percent / Decimal("100")).quantize(
        TWO_PLACES, rounding=ROUND_HALF_UP)
