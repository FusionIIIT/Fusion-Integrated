"""Creating a leave request and putting it into the workflow.

Validation happens here, once, before anything is written: category
eligibility, balance, calendar, overlap. A request that reaches the workflow
has already been checked against the policy in force.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.db import transaction

from core.api.exceptions import BadRequestError, ConflictError
from modules.leave.domain import authority
from modules.leave.domain.categories import (
    Category,
    allows_half_day,
    counts_intervening_days,
)
from modules.leave.domain.counting import Half, chargeable_days
from modules.leave.domain.entitlement import has_sufficient_balance
from modules.leave.domain.overlap import Period, first_conflict
from modules.leave.domain.state_machine import Actor, Event, State
from modules.leave.models import AuthorityRule, LeaveRequest, SubstituteNomination
from modules.leave.selectors import balances
from modules.leave.selectors import policy as policy_selector
from modules.leave.services.workflow import apply_event

ACTIVE_STATES = tuple(
    s.value
    for s in State
    if s
    not in {
        State.DRAFT,
        State.REJECTED,
        State.WITHDRAWN,
        State.CANCELLED,
        State.CLOSED,
    }
)


def _candidates(policy_id: int, category: Category) -> list[authority.AuthorityCandidate]:
    rows = AuthorityRule.objects.filter(policy_id=policy_id, category=category.value)
    return [
        authority.AuthorityCandidate(
            category=Category(r.category),
            unit=r.unit,
            designation=r.designation,
            applies_to_faculty=r.applies_to_faculty,
            establishment_step=r.establishment_step,
            sanctioning_designation=r.sanctioning_designation,
            self_sanction=r.self_sanction,
            specificity=r.specificity,
        )
        for r in rows
    ]


def existing_periods(user_id: int, ignore_request_id: int | None = None) -> list[Period]:
    """Everything already pending or approved for this person. BR-EL-012."""
    qs = LeaveRequest.objects.filter(user_id=user_id, state__in=ACTIVE_STATES)
    if ignore_request_id is not None:
        qs = qs.exclude(pk=ignore_request_id)
    return [
        Period(r.starts_on, r.ends_on, Half(r.half) if r.half else None)
        for r in qs.only("starts_on", "ends_on", "half")
    ]


def validate(
    *,
    user_id: int,
    category: Category,
    starts_on: date,
    ends_on: date,
    half: Half | None,
    faculty: bool,
    ignore_request_id: int | None = None,
) -> tuple[Decimal, int, int]:
    """Check a request against the effective policy. Returns days, policy, calendar."""
    if ends_on < starts_on:
        raise BadRequestError("Leave cannot end before it starts.", code="period_invalid")
    if half is not None and not allows_half_day(category):
        raise BadRequestError(
            f"{category.value} cannot be taken as a half day.", code="half_day_not_allowed"
        )

    effective = policy_selector.effective_policy(starts_on)
    calendar = policy_selector.effective_calendar(starts_on.year)

    if category is Category.RH:
        allowed = policy_selector.restricted_days(calendar)
        if starts_on not in allowed or starts_on != ends_on:
            raise BadRequestError(
                "A restricted holiday request must name one published RH date.",
                code="rh_date_invalid",
            )

    if category is Category.VL:
        windows = calendar.vacation_periods.all()
        inside = any(w.starts_on <= starts_on and ends_on <= w.ends_on for w in windows)
        if not inside:
            raise BadRequestError(
                "Vacation leave must fall inside a published vacation period.",
                code="outside_vacation_period",
            )

    days = chargeable_days(
        category, starts_on, ends_on, policy_selector.closed_days(calendar), half=half
    )
    if days <= 0:
        raise BadRequestError(
            "The requested period contains no chargeable days.", code="no_chargeable_days"
        )

    clash = first_conflict(
        Period(starts_on, ends_on, half), existing_periods(user_id, ignore_request_id)
    )
    if clash is not None:
        raise ConflictError(
            f"This overlaps leave you already hold from {clash.start} to {clash.end}.",
            code="overlapping_leave",
        )

    balance = balances.balance_for(user_id, starts_on.year, category)
    if not has_sufficient_balance(balance, days):
        raise ConflictError(
            f"{days} day(s) requested but {balance.available} available in {category.value}.",
            code="insufficient_balance",
        )
    return days, effective.pk, calendar.pk


@transaction.atomic
def submit(
    *,
    user_id: int,
    category: Category,
    starts_on: date,
    ends_on: date,
    reason: str,
    faculty: bool,
    unit: str = "",
    designation: str = "",
    half: Half | None = None,
    substitute_user_id: int | None = None,
    station: dict | None = None,
) -> LeaveRequest:
    """Create a request and put it into the workflow. EL-UC-001."""
    days, policy_id, calendar_id = validate(
        user_id=user_id,
        category=category,
        starts_on=starts_on,
        ends_on=ends_on,
        half=half,
        faculty=faculty,
    )
    if substitute_user_id == user_id:
        raise BadRequestError(
            "An employee cannot stand in for themselves.", code="substitute_is_applicant"
        )

    rule = authority.select_rule(
        _candidates(policy_id, category), category, unit, designation, faculty
    )
    route = authority.route_for(
        rule, category, substitute_required=substitute_user_id is not None
    )
    if not unit and not route.self_sanction:
        # The review queue is keyed on the unit, so a request without one would
        # be accepted, enter the workflow, and appear in nobody's queue. Better
        # refused at the door than lost silently for a fortnight.
        raise BadRequestError(
            "Your record has no department, so there is no unit head to review "
            "this. Ask the establishment section to set it before applying.",
            code="applicant_has_no_unit",
        )

    station = station or {}
    request = LeaveRequest.objects.create(
        user_id=user_id,
        category=category.value,
        state=State.DRAFT.value,
        starts_on=starts_on,
        ends_on=ends_on,
        half=half.value if half else "",
        reason=reason,
        requested_days=days,
        policy_id=policy_id,
        calendar_id=calendar_id,
        unit=unit,
        station_leave=bool(station),
        station_destination=station.get("destination", ""),
        station_from=station.get("from"),
        station_to=station.get("to"),
    )
    if substitute_user_id is not None:
        SubstituteNomination.objects.create(
            request=request, substitute_user_id=substitute_user_id
        )
    return apply_event(
        request,
        Event.SUBMIT,
        Actor.EMPLOYEE,
        actor_user_id=user_id,
        target=route.first_state,
    )


def counts_weekends(category: Category) -> bool:
    return counts_intervening_days(category)
