"""Gathering the facts a rule needs.

Everything a rule reads comes from here, so a new caller cannot quietly pass a
balance that was never adjusted for the requests already pending.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.utils import timezone

from modules.directory import contracts as directory
from modules.leave.domain import categories as cat
from modules.leave.domain import routing, validation
from modules.leave.domain.substitutes import Interval, NominationFacts
from modules.leave.domain.substitutes import validate_nomination as check_nomination
from modules.leave.models import LeaveRequest
from modules.leave.selectors import accounts as account_selector
from modules.leave.selectors import config as config_selector
from modules.leave.selectors import requests as request_selector


def person(user_id: int):
    """The directory's view of a person, or None when IAM cannot answer."""
    return directory.get_users([user_id]).get(user_id)


def is_faculty(user_id: int) -> bool:
    return getattr(person(user_id), "kind", "") == "faculty"


def policy():
    return config_selector.current_policy()


def path_for(row: LeaveRequest) -> routing.Path:
    """The configured path for this request, resolved from current settings."""
    current = policy()
    return routing.resolve(
        category=row.category,
        steps=config_selector.hierarchy_steps(),
        self_sanction_designation=current.self_sanction_designation,
        applicant_role=row.applicant_role,
    )


def evaluate(row: LeaveRequest, *, today: date | None = None) -> Decimal:
    """Validate one request against the current configuration (BR-EL-001..013)."""
    today = today or timezone.localdate()
    year = row.start_date.year
    exclude = row.pk if row.kind == "new" else row.parent_id
    facts = validation.RequestFacts(
        user_id=row.user_id,
        category=row.category,
        start=row.start_date,
        end=row.end_date,
        half=row.half,
        is_faculty=row.applicant_is_faculty,
        balance=account_selector.balance(user_id=row.user_id, year=year,
                                        category=row.category),
        committed=account_selector.committed(user_id=row.user_id, year=year,
                                            category=row.category),
        active_intervals=request_selector.intervals_for(row.user_id,
                                                        exclude_pk=exclude),
        closed_dates=config_selector.closed_dates(row.start_date, row.end_date),
        restricted_holiday_dates=config_selector.restricted_holiday_dates(
            row.start_date, row.end_date),
        vacation_periods=config_selector.vacation_periods(),
        today=today,
        max_backdate_days=policy().max_backdate_days,
    )
    return validation.days_required(facts)


def check_substitute(*, row: LeaveRequest, substitute_user_id: int) -> None:
    """BR-EL-014: refuse an ineligible nominee before the gate is even set."""
    nominee = person(substitute_user_id)
    check_nomination(NominationFacts(
        applicant_id=row.user_id,
        nominee_id=substitute_user_id,
        nominee_is_employee=getattr(nominee, "kind", "") in ("faculty", "staff"),
        nominee_is_active=bool(getattr(nominee, "is_active", True)) if nominee else False,
        period=Interval(start=row.start_date, end=row.end_date,
                        category=row.category, half=row.half),
        nominee_intervals=request_selector.intervals_for(substitute_user_id),
    ))


def categories_for_request() -> tuple[str, ...]:
    return cat.CATEGORIES


def has_evidence(row: LeaveRequest) -> bool:
    """BR-EL-009: COL may need medical evidence; a missing note is not fatal."""
    return bool((row.evidence_note or "").strip())
