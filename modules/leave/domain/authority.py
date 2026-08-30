"""Where a request goes after it is submitted, and who ends it.

BR-EL-016 to BR-EL-020. The path depends on the category, the applicant's unit
and their designation. Nothing here names an office: the candidate rules are
supplied by the caller from configuration, and this decides which one applies
and what it implies.
"""
from __future__ import annotations

from dataclasses import dataclass

from modules.leave.domain.categories import Category, needs_higher_sanction
from modules.leave.domain.state_machine import State


@dataclass(frozen=True)
class AuthorityCandidate:
    """One configured rule, as read from the database."""

    #: Empty matches any unit, so a general rule needs one row.
    category: Category
    unit: str
    designation: str
    applies_to_faculty: bool | None
    establishment_step: bool
    sanctioning_designation: str
    self_sanction: bool
    specificity: int


@dataclass(frozen=True)
class Route:
    """What the workflow should do with this request."""

    first_state: State
    establishment_step: bool
    sanctioning_designation: str
    self_sanction: bool
    unit_head_is_final: bool


class NoAuthorityConfigured(Exception):
    """Nothing matches, so there is nobody to send the request to."""


def _matches(
    rule: AuthorityCandidate, category: Category, unit: str, designation: str,
    faculty: bool,
) -> bool:
    if rule.category is not category:
        return False
    if rule.unit and rule.unit != unit:
        return False
    if rule.designation and rule.designation != designation:
        return False
    return not (
        rule.applies_to_faculty is not None and rule.applies_to_faculty is not faculty
    )


def select_rule(
    candidates: list[AuthorityCandidate],
    category: Category,
    unit: str,
    designation: str,
    faculty: bool,
) -> AuthorityCandidate:
    """The most specific matching rule.

    Ties are broken by how much the rule actually constrains, so a rule naming
    a unit and a designation beats one naming only the category. An explicit
    specificity on the row wins over both, which is the escape hatch for a case
    the ordering does not anticipate.
    """
    matches = [
        r for r in candidates if _matches(r, category, unit, designation, faculty)
    ]
    if not matches:
        raise NoAuthorityConfigured(
            f"no authority rule for {category.value} in unit {unit!r}"
        )

    def weight(r: AuthorityCandidate) -> tuple[int, int, int, int]:
        return (
            r.specificity,
            1 if r.unit else 0,
            1 if r.designation else 0,
            1 if r.applies_to_faculty is not None else 0,
        )
    return max(matches, key=weight)


def route_for(
    rule: AuthorityCandidate, category: Category, *, substitute_required: bool
) -> Route:
    """Where the request starts and how it will end."""
    if rule.self_sanction:
        first = State.AWAITING_SELF_SANCTION
    elif substitute_required:
        first = State.AWAITING_SUBSTITUTE
    else:
        first = State.AWAITING_UNIT_HEAD

    unit_head_final = not needs_higher_sanction(category)
    return Route(
        first_state=first,
        establishment_step=rule.establishment_step and not unit_head_final,
        sanctioning_designation=rule.sanctioning_designation,
        self_sanction=rule.self_sanction,
        unit_head_is_final=unit_head_final,
    )


def after_unit_head(route: Route) -> State:
    """Where a recommendation goes next. BW-EL-03 rows 5 and 6."""
    if route.unit_head_is_final:
        return State.APPROVED_NOT_STARTED
    if route.establishment_step:
        return State.AWAITING_ESTABLISHMENT
    return State.AWAITING_FINAL_SANCTION


def after_unit_head_for_cancellation(route: Route) -> State:
    """The same fork on the cancellation path. BW-EL-05."""
    if route.unit_head_is_final:
        return State.CANCELLED
    if route.establishment_step:
        return State.CANCELLATION_ESTABLISHMENT
    return State.CANCELLATION_FINAL
