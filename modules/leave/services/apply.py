"""Leave application submission service."""

from __future__ import annotations

import datetime

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, DomainError
from modules.leave.domain import errors, rules
from modules.leave.domain.counting import count_leave_days
from modules.leave.domain.state_machine import LeaveState
from modules.leave.models import LeaveRequest, LeaveTransition, LedgerEntry, SlaClock
from modules.leave.selectors.balances import get_user_balance
from modules.leave.selectors.calendars import (
    get_active_calendar,
    get_calendar_holidays,
    get_restricted_holidays,
    get_vacation_ranges,
)
from modules.leave.selectors.policy import get_active_policy, resolve_authority_route
from modules.leave.selectors.requests import (
    check_applicant_overlap,
    check_substitute_availability,
)


def submit_leave_request(
    user_id: int,
    category: str,
    starts_on: datetime.date,
    ends_on: datetime.date,
    reason: str,
    half: str = "none",
    evidence_reference: str = "",
    substitute_user_id: int | None = None,
    station: dict | None = None,
    is_faculty: bool = True,
    designation: str = "",
    unit: str = "",
) -> LeaveRequest:
    """Creates and submits a new leave application under EL-UC-001."""
    try:
        rules.validate_category_eligibility(category, is_faculty)
        rules.validate_substitute(user_id, substitute_user_id)
    except errors.LeaveDomainError as e:
        raise DomainError(str(e), code=e.code) from e

    # Date and calendar checks
    year = starts_on.year
    calendar = get_active_calendar(year)
    holidays = get_calendar_holidays(calendar) if calendar else set()

    if category == "RH":
        rh_dates = get_restricted_holidays(calendar) if calendar else []
        try:
            rules.validate_restricted_holiday(starts_on, ends_on, rh_dates)
        except errors.LeaveDomainError as e:
            raise DomainError(str(e), code=e.code) from e

    if category == "VL":
        vacations = get_vacation_ranges(calendar) if calendar else []
        try:
            rules.validate_vacation_period(starts_on, ends_on, vacations)
        except errors.LeaveDomainError as e:
            raise DomainError(str(e), code=e.code) from e

    requested_days = count_leave_days(category, starts_on, ends_on, half, holidays)

    # Overlap validation under BR-EL-012
    try:
        check_applicant_overlap(user_id, starts_on, ends_on, half)
    except errors.LeaveDomainError as e:
        raise ConflictError(str(e)) from e

    # Substitute availability under BR-EL-014
    if substitute_user_id and not check_substitute_availability(
        substitute_user_id, starts_on, ends_on
    ):
        raise ConflictError(
            "The nominated substitute has conflicting active leave during this period."
        )

    # Balance check
    available_balance = get_user_balance(user_id, year, category)
    try:
        rules.validate_balance(available_balance, requested_days)
    except errors.LeaveDomainError as e:
        raise ConflictError(str(e)) from e

    # Hierarchy and sanction resolution
    policy = get_active_policy(starts_on)
    sanctioning_desig = ""
    is_director = designation == "Director"
    if policy:
        route = resolve_authority_route(policy, category, unit, designation, is_faculty)
        if route:
            sanctioning_desig = route.sanctioning_designation

    with transaction.atomic():
        initial_state = LeaveState.PENDING_REVIEW
        if substitute_user_id:
            initial_state = LeaveState.SUBMITTED_PENDING_SUBSTITUTE
        elif is_director:
            initial_state = LeaveState.APPROVED

        station_active = bool(station and station.get("destination"))
        station_dest = station.get("destination", "") if station else ""

        req = LeaveRequest.objects.create(
            user_id=user_id,
            category=category,
            state=initial_state,
            starts_on=starts_on,
            ends_on=ends_on,
            half=half,
            reason=reason,
            evidence_reference=evidence_reference,
            requested_days=requested_days,
            actual_days=requested_days if initial_state == LeaveState.APPROVED else None,
            station_leave=station_active,
            station_destination=station_dest,
            substitute_user_id=substitute_user_id,
            sanctioning_designation=sanctioning_desig,
            decided_at=timezone.now() if initial_state == LeaveState.APPROVED else None,
        )

        LeaveTransition.objects.create(
            request=req,
            from_state=LeaveState.DRAFT,
            to_state=initial_state,
            event="submit",
            actor_role=designation or "Employee",
            actor_user_id=user_id,
            remark=reason,
            workflow_ref="CW-EL-01",
        )

        if initial_state == LeaveState.APPROVED:
            LedgerEntry.objects.create(
                user_id=user_id,
                year=year,
                category=category,
                days=-abs(requested_days),
                reason="consumption",
                request_id=req.pk,
                note=f"Director self-sanctioned leave {req.pk}",
            )

        SlaClock.objects.create(request=req, state=initial_state)

        return req
