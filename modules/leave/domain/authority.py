"""Where a request goes after it is submitted, and who ends it."""
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
    rule: AuthorityCandidate,
    category: Category,
    unit: str,
    designations: frozenset[str],
    faculty: bool,
) -> bool:
    if rule.category is not category:
        return False
    if rule.unit and rule.unit != unit:
        return False
    if rule.designation and rule.designation not in designations:
        return False
    return not (
        rule.applies_to_faculty is not None and rule.applies_to_faculty is not faculty
    )


def select_rule(
    candidates: list[AuthorityCandidate],
    category: Category,
    unit: str,
    designations: frozenset[str] | set[str] | str,
    faculty: bool,
) -> AuthorityCandidate:
    """The most specific matching rule."""
    # People hold a rank and an office at once, so match the whole set.
    held = frozenset({designations} if isinstance(designations, str) else designations)
    matches = [r for r in candidates if _matches(r, category, unit, held, faculty)]
    if not matches:
        raise NoAuthorityConfigured(
            f"No approval path is configured for {category.value} in "
            f"{unit or 'your unit'}. The leave administrator has to add an "
            "authority rule before this leave can be applied for."
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

    # BR-EL-018 sets the floor: SCL, EL, COL and VL go above the unit head.
    above_unit_head = needs_higher_sanction(category) or bool(
        rule.sanctioning_designation)
    if needs_higher_sanction(category) and not (
            rule.sanctioning_designation or rule.self_sanction):
        raise NoAuthorityConfigured(
            f"{category.value} must be sanctioned above the unit head, but the rule "
            f"for {rule.unit or 'any unit'} names no sanctioning designation. The "
            "leave administrator has to complete it.")

    unit_head_final = not above_unit_head
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
