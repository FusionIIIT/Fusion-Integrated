"""ELM workflow transition policy; persistence and authorization live in services."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import re


class TransitionError(ValueError):
    pass


@dataclass(frozen=True)
class RouteStep:
    role: str
    decision_kind: str


def normalize_role(role: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", role.casefold()).strip("_")


def route_for(*, category: str, is_director: bool, establishment_role: str | None,
              final_authority_role: str | None) -> tuple[RouteStep, ...]:
    """Resolve the current configured route shape, leaving user assignment to IAM/HR."""
    if is_director:
        return (RouteStep("director", "final"),)
    if category in {"CL", "RH"}:
        return (RouteStep("unit_head", "final"),)
    if not final_authority_role:
        raise TransitionError("No final sanctioning authority is configured")
    steps = [RouteStep("unit_head", "recommendation")]
    if establishment_role:
        steps.append(RouteStep("establishment", "forward"))
    steps.append(RouteStep(normalize_role(final_authority_role), "final"))
    return tuple(steps)


def after_substitute_response(*, accepted: bool, declined_before: int,
                              replacement_limit: int = 1) -> str:
    """Return next state while enforcing the specified replacement traversal."""
    if accepted:
        return "pending_unit_head"
    if declined_before >= replacement_limit:
        return "applicant_action"
    return "applicant_action"


def validate_withdrawal(status: str) -> None:
    if status not in {"awaiting_substitute", "applicant_action", "pending_unit_head",
                      "pending_establishment", "pending_authority"}:
        raise TransitionError("Only a pending request can be withdrawn")


def validate_cancellation(*, status: str, start_date: date, today: date) -> None:
    if status != "approved":
        raise TransitionError("Only approved leave can be cancelled")
    if start_date <= today:
        raise TransitionError("Approved leave can only be cancelled before its start date")


def validate_extension(*, category: str, status: str, start_date: date, end_date: date,
                       new_end_date: date, today: date) -> None:
    if category not in {"EL", "COL", "VL"}:
        raise TransitionError("Only EL, COL, or VL may be extended")
    if status != "approved" or not (start_date <= today <= end_date):
        raise TransitionError("An extension is allowed only while approved leave is ongoing")
    if new_end_date <= end_date:
        raise TransitionError("An extension must add at least one day")


def resumption_outcome(*, approved_end_date: date, actual_resume_date: date) -> str:
    if actual_resume_date < approved_end_date:
        return "early"
    if actual_resume_date > approved_end_date:
        return "late"
    return "normal"
