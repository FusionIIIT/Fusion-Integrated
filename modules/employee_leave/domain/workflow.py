"""Pure ELM request validation and workflow transitions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


class InvalidLeaveRequest(ValueError):
    pass


class InvalidLeaveTransition(ValueError):
    pass


@dataclass(frozen=True)
class RequestFacts:
    leave_type: str
    start_date: date
    end_date: date
    half_day: bool = False
    requires_substitute: bool = False
    higher_sanction: bool = False
    is_director: bool = False


def charged_days(
    start: date, end: date, *, half_day: bool = False, holidays: frozenset[date] = frozenset()
) -> Decimal:
    """Count the continuous inclusive period; configured holidays are not deducted."""
    if end < start:
        raise InvalidLeaveRequest("The end date must not precede the start date.")
    if half_day:
        if start != end:
            raise InvalidLeaveRequest("Half-day leave must start and end on the same day.")
        return Decimal("0.5")
    count = (end - start).days + 1
    if count < 1:
        raise InvalidLeaveRequest("A leave request must span at least one day.")
    return Decimal(count)


def initial_state(facts: RequestFacts) -> str:
    if facts.half_day and facts.leave_type != "CL":
        raise InvalidLeaveRequest("Half-day leave is available for Casual Leave only.")
    if facts.requires_substitute:
        return "substitute_pending"
    if facts.leave_type in {"CL", "RH"}:
        return "unit_head_pending"
    if facts.is_director:
        return "final_pending"
    return "unit_head_pending"


_TRANSITIONS = {
    ("substitute_pending", "accept_substitute"): "unit_head_pending",
    ("substitute_pending", "decline_substitute"): "substitute_declined",
    ("unit_head_pending", "recommend"): "final_pending",
    ("unit_head_pending", "route_establishment"): "establishment_pending",
    ("unit_head_pending", "approve"): "approved",
    ("unit_head_pending", "reject"): "rejected",
    ("establishment_pending", "route_final"): "final_pending",
    ("establishment_pending", "return_to_unit_head"): "unit_head_pending",
    ("establishment_pending", "reject"): "rejected",
    ("final_pending", "approve"): "approved",
    ("final_pending", "reject"): "rejected",
    ("resumption_pending", "review"): "resumption_reviewed",
    ("substitute_declined", "nominate_substitute"): "substitute_pending",
    ("cancellation_unit_head_pending", "approve_cancellation"): "cancelled",
    ("cancellation_unit_head_pending", "reject_cancellation"): "rejected",
    ("cancellation_unit_head_pending", "recommend_cancellation"): "cancellation_final_pending",
    (
        "cancellation_unit_head_pending",
        "route_cancellation_establishment",
    ): "cancellation_establishment_pending",
    (
        "cancellation_establishment_pending",
        "route_cancellation_final",
    ): "cancellation_final_pending",
    (
        "cancellation_establishment_pending",
        "return_cancellation_to_unit_head",
    ): "cancellation_unit_head_pending",
    ("cancellation_establishment_pending", "reject_cancellation"): "rejected",
    ("cancellation_final_pending", "approve_cancellation"): "cancelled",
    ("cancellation_final_pending", "reject_cancellation"): "rejected",
}


def transition(state: str, action: str) -> str:
    try:
        return _TRANSITIONS[(state, action)]
    except KeyError as exc:
        raise InvalidLeaveTransition(
            f"Action {action!r} is not valid while a request is {state!r}."
        ) from exc


def validate_extension(*, leave_type: str, start: date, end: date) -> None:
    if leave_type not in {"EL", "COL", "VL"}:
        raise InvalidLeaveRequest("Only Earned, Commuted, or Vacation Leave can be extended.")
    if end < start:
        raise InvalidLeaveRequest("The extension end date must not precede its start date.")
