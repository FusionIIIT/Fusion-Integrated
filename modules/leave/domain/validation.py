"""Deterministic ELM counting and application validation rules."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import Iterable


CONTINUOUS_CATEGORIES = frozenset({"EL", "COL", "VL"})
SUPPORTED_CATEGORIES = frozenset({"CL", "RH", "SCL", "EL", "COL", "VL"})


@dataclass(frozen=True)
class ValidationResult:
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    @property
    def is_valid(self) -> bool:
        return not self.errors


def dates_inclusive(start: date, end: date) -> Iterable[date]:
    day = start
    while day <= end:
        yield day
        day += timedelta(days=1)


def calculate_duration(
    category: str, start: date, end: date, *, cl_portion: str = "full",
    holidays: Iterable[date] = (), rh_dates: Iterable[date] = (),
) -> Decimal:
    """Count ELM leave days, including half-day CL and category calendars."""
    if end < start:
        raise ValueError("end_date must be on or after start_date")
    if category not in SUPPORTED_CATEGORIES:
        raise ValueError(f"Unsupported leave category: {category}")
    holiday_set, rh_set = set(holidays), set(rh_dates)
    days = tuple(dates_inclusive(start, end))
    if category in CONTINUOUS_CATEGORIES:
        return Decimal(len(days))
    if category == "RH":
        if len(days) != 1 or start not in rh_set:
            raise ValueError("RH must be a date in the effective published RH calendar")
        return Decimal("1")
    if category == "CL":
        if cl_portion not in {"full", "first_half", "second_half"}:
            raise ValueError("Invalid CL portion")
        if cl_portion != "full" and len(days) != 1:
            raise ValueError("Half-day CL must cover one date")
        units = sum(day.weekday() < 5 and day not in holiday_set for day in days)
        amount = Decimal(units)
        return amount / 2 if cl_portion != "full" else amount
    # SCL follows the institute's working-day calendar; no separate
    # encoded purpose-admissibility or employee-kind rule exists in baseline.
    return Decimal(sum(day.weekday() < 5 and day not in holiday_set for day in days))


def validate_application(
    *, category: str, start: date, end: date, employee_kind: str,
    cl_portion: str = "full", station_leave: bool = False,
    station_destination: str = "", station_departure_at=None,
    station_return_at=None, holidays: Iterable[date] = (),
    rh_dates: Iterable[date] = (), available: Decimal | None = None,
    overlapping: Iterable[tuple[date, date, str, str]] = (),
    medical_evidence_ref: str = "", medical_required: bool = False,
    vacation_periods: Iterable[tuple[date, date]] = (),
) -> ValidationResult:
    """Validate eligibility, calendar, overlap, evidence, and balance."""
    errors: list[str] = []
    warnings: list[str] = []
    if category not in SUPPORTED_CATEGORIES:
        errors.append("Unsupported leave category")
    if end < start:
        errors.append("End date must be on or after start date")
    if employee_kind not in {"faculty", "staff"}:
        errors.append("ELM is available to Faculty and Staff employees only")
    if category == "EL" and employee_kind == "faculty":
        errors.append("EL entitlement is assigned to non-faculty employees")
    if category == "VL":
        if employee_kind != "faculty":
            errors.append("VL is available to faculty only")
        elif not any(start >= lo and end <= hi for lo, hi in vacation_periods):
            errors.append("VL dates must fall inside an Academic Calendar vacation period")
    if station_leave and (not station_destination.strip() or not station_departure_at or not station_return_at):
        errors.append("Station Leave requires destination, departure, and return details")
    if station_leave and station_return_at and station_departure_at and station_return_at <= station_departure_at:
        errors.append("Station Leave return must be after departure")
    if category == "COL" and medical_required and not medical_evidence_ref.strip():
        errors.append("Medical evidence is required for this COL request")
    if start <= end and category in SUPPORTED_CATEGORIES:
        try:
            requested = calculate_duration(category, start, end, cl_portion=cl_portion, holidays=holidays, rh_dates=rh_dates)
        except ValueError as exc:
            errors.append(str(exc))
        else:
            if requested <= 0:
                errors.append("The requested period contains no chargeable leave days")
            if available is not None and requested > available:
                errors.append(f"Insufficient balance: {available} available, {requested} requested")
            for prior_start, prior_end, prior_category, prior_portion in overlapping:
                is_other_half = (
                    category == prior_category == "CL"
                    and start == end == prior_start == prior_end
                    and cl_portion in {"first_half", "second_half"}
                    and prior_portion in {"first_half", "second_half"}
                    and cl_portion != prior_portion
                )
                if not is_other_half and prior_start <= end and prior_end >= start:
                    errors.append(f"Request overlaps active {prior_category} leave from {prior_start} to {prior_end}")
                    break
    return ValidationResult(tuple(dict.fromkeys(errors)), tuple(warnings))
