"""Pure-Python ELM policy helpers. Keep this layer independent of Django/DRF."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

SUPPORTED_CATEGORIES = ("CL", "RH", "SCL", "EL", "COL", "VL")
CONTINUOUS_CATEGORIES = frozenset({"EL", "COL", "VL"})
NON_CARRY_FORWARD = frozenset({"CL", "RH", "SCL", "VL"})
ACTIVE_REQUEST_STATUSES = frozenset({
    "awaiting_substitute", "awaiting_unit_head", "awaiting_establishment",
    "awaiting_sanction", "awaiting_cancellation_unit_head",
    "awaiting_cancellation_sanction", "awaiting_resumption_review",
    "action_required",
})

DEFAULT_ENTITLEMENTS = {
    "CL": Decimal("8.00"),
    "RH": Decimal("2.00"),
    "SCL": Decimal("15.00"),
    "EL": Decimal("30.00"),
    "COL": Decimal("20.00"),
    "VL": Decimal("60.00"),
}


def entitlement_for(category: str, employee_kind: str) -> Decimal:
    """Return baseline annual entitlement for a directory employee kind."""
    if category not in SUPPORTED_CATEGORIES:
        raise ValueError(f"Unsupported leave category: {category}")
    if employee_kind not in {"faculty", "staff"}:
        raise ValueError("Only institute faculty and staff may use ELM.")
    if category == "EL" and employee_kind != "staff":
        return Decimal("0.00")
    if category == "VL" and employee_kind != "faculty":
        return Decimal("0.00")
    return DEFAULT_ENTITLEMENTS[category]


def count_leave_days(
    category: str,
    start_date: date,
    end_date: date,
    closed_dates: set[date] | frozenset[date] = frozenset(),
    cl_half: str = "none",
    continuous_counting: bool | None = None,
) -> Decimal:
    """Count leave days under the synchronized baseline.

    The continuous-calendar versus working-day counting mode can be supplied
    from the active leave policy. CL half-days apply only to one open weekday;
    RH is a one-day selection validated against the published holiday calendar.
    Distinct first/second CL halves are handled by service-layer overlap checks.
    """
    if category not in SUPPORTED_CATEGORIES:
        raise ValueError(f"Unsupported leave category: {category}")
    if start_date > end_date:
        raise ValueError("The start date must not be after the end date.")
    if cl_half not in {"none", "first", "second"}:
        raise ValueError("CL half-day must be none, first, or second.")
    if cl_half != "none":
        if category != "CL" or start_date != end_date:
            raise ValueError("Half-day selection is valid only for one-date CL.")
        if start_date.weekday() >= 5 or start_date in closed_dates:
            return Decimal("0.00")
        return Decimal("0.50")

    if category == "RH":
        if start_date != end_date:
            raise ValueError("An RH request must cover one applicable restricted holiday.")
        # Restricted holidays are selected explicitly from the calendar; they
        # count as one unit even when the date is marked as a calendar closure.
        return Decimal("1.00")

    is_continuous = (
        category in CONTINUOUS_CATEGORIES
        if continuous_counting is None
        else continuous_counting
    )
    if is_continuous:
        return Decimal((end_date - start_date).days + 1)

    count = 0
    current = start_date
    while current <= end_date:
        if current.weekday() < 5 and current not in closed_dates:
            count += 1
        current += timedelta(days=1)
    return Decimal(count)


def ranges_overlap(a_start: date, a_end: date, b_start: date, b_end: date) -> bool:
    return a_start <= b_end and b_start <= a_end
