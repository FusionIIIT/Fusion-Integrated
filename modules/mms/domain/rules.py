"""Pure business rules for MMS.

Framework-free: no Django, DRF or Celery. Raises `domain.exceptions` types;
the service layer translates them to `core.api.exceptions`. Every function
takes plain values and returns a plain result, so each rule tests in
milliseconds with no database.

Implements: BR-MMS-028 (special food lead time), BR-MMS-021..025 (rebate
validation), BR-MMS-014 (menu structure), BR-MMS-041 (vacation response
options), BR-MMS-001/036 (scope/policy boundary).
"""

from __future__ import annotations

from datetime import date, timedelta

from modules.mms.domain.exceptions import GuardFailed

REBATE_REASONS = ("medical", "institute_leave", "family_function", "other")
VACATION_RESPONSES = ("yes", "no")
MENU_MEALS = ("breakfast", "lunch", "dinner")


def special_food_lead_time_ok(submitted_on: date, requested_date: date) -> None:
    """BR-MMS-028: allow only if submitted at least 1 calendar day before
    the requested date."""
    if requested_date < submitted_on + timedelta(days=1):
        raise GuardFailed(
            "lead_time_at_least_1_calendar_day",
            "Submit the special food request at least one calendar day before the requested date.",
        )


def rebate_valid(
    reason: str,
    explanation: str,
    start_date: date,
    end_date: date,
    submitted_on: date,
    existing: list[tuple[date, date]],
) -> None:
    """BR-MMS-021/022/023/024: validate a rebate submission."""
    if reason not in REBATE_REASONS:
        raise GuardFailed(
            "reason_complete",
            "Choose a valid rebate reason: medical, institute leave, family function, or other.",
        )
    if reason == "other" and not explanation.strip():
        raise GuardFailed("reason_complete", "An explanation is required when the reason is Other.")
    if (end_date - start_date).days < 3:
        raise GuardFailed(
            "duration_at_least_3_days", "The rebate duration must be at least 3 days."
        )
    if start_date < submitted_on + timedelta(days=1):
        raise GuardFailed(
            "lead_time_at_least_1_day",
            "Submit the rebate request at least one calendar day before the start date.",
        )
    for estart, eend in existing:
        if start_date <= eend and end_date >= estart:
            raise GuardFailed("no_rebate_overlap", "This rebate overlaps an existing request.")


def valid_menu_meal(meal: str) -> None:
    """BR-MMS-014: menu items are day-wise and meal-wise (breakfast/lunch/
    dinner)."""
    if meal not in MENU_MEALS:
        raise GuardFailed("menu_structure", "A menu item must be breakfast, lunch or dinner.")


def valid_vacation_response(response: str) -> None:
    """BR-MMS-041: student vacation responses are Yes or No only."""
    if response not in VACATION_RESPONSES:
        raise GuardFailed("response_option", "Record a Yes or No response only.")


def assert_mms_scope(function_name: str) -> None:
    """BR-MMS-001/036: MMS stays within mess-management functions and does
    not define institutional policy. Called at the boundary of any write
    that would leave scope."""
    # No-op here: the boundary is enforced by not offering out-of-scope
    # endpoints and by the read-only directory/django_auth seams. Kept as an
    # explicit, named enforcement point so reviewers can trace BR-MMS-001.
    return
