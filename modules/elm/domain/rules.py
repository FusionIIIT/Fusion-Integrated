"""Input invariants that can be enforced without assuming leave policy."""

from datetime import date
from decimal import Decimal, InvalidOperation

ALLOWED_HALF_DAY_SESSIONS = {"FN", "AN"}


def validate_leave_details(
    *,
    start_date: date,
    end_date: date,
    duration_days: Decimal,
    is_half_day: bool,
    half_day_session: str,
    leave_type: str,
    reason: str,
    station_leave: bool,
    station_leave_address: str,
    out_of_station_from: date | None,
    out_of_station_to: date | None,
) -> Decimal:
    """Reject internally inconsistent submissions without calculating entitlements.

    The complete ELM policy package is not present in this repository, so
    working-day calendars and leave-category quotas deliberately stay outside
    this validation function.
    """
    try:
        duration = Decimal(str(duration_days))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("Duration must be a valid number of days.") from exc

    if duration <= 0:
        raise ValueError("Duration must be greater than zero.")
    if duration * 2 != (duration * 2).to_integral_value():
        raise ValueError("Duration must be in half-day increments.")
    if end_date < start_date:
        raise ValueError("End date must be on or after start date.")
    if duration > Decimal((end_date - start_date).days + 1):
        raise ValueError("Duration cannot exceed the calendar span of the requested dates.")
    if not reason.strip():
        raise ValueError("A reason is required.")

    if is_half_day:
        if leave_type != "CL":
            raise ValueError("Half-day requests are supported only for Casual Leave.")
        if start_date != end_date or duration != Decimal("0.5"):
            raise ValueError("A half-day request must cover one date and use 0.5 days.")
        if half_day_session not in ALLOWED_HALF_DAY_SESSIONS:
            raise ValueError("Choose a valid half-day session.")
    elif half_day_session:
        raise ValueError("A half-day session is only valid for a half-day request.")
    elif duration < 1:
        raise ValueError("A request shorter than one day must be marked as a half-day.")

    station_dates = (out_of_station_from, out_of_station_to)
    if station_leave:
        if not station_leave_address.strip():
            raise ValueError("An address is required for station leave.")
        if any(value is None for value in station_dates):
            raise ValueError("Departure and return dates are required for station leave.")
        if out_of_station_to < out_of_station_from:
            raise ValueError("Return date must be on or after departure date.")
    elif station_leave_address.strip() or any(value is not None for value in station_dates):
        raise ValueError("Station leave details require station leave to be selected.")

    return duration
