from enum import Enum
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import List, Optional

class LeaveCategory(Enum):
    CL = "Casual Leave"
    RH = "Restricted Holiday"
    SCL = "Special Casual Leave"
    EL = "Earned Leave"
    COL = "Compensatory Off Leave"
    VL = "Vacation Leave"

class MissingLeaveFactsError(Exception):
    pass

class UnresolvedLeavePolicyError(Exception):
    pass

@dataclass
class HolidayCalendar:
    holidays: List[date]
    published: bool
    effective_from: date
    effective_to: date

@dataclass
class VacationPeriod:
    start_date: date
    end_date: date

def validate_category(category: LeaveCategory) -> None:
    if not isinstance(category, LeaveCategory):
        raise ValueError(f"Invalid leave category: {category!r}")

def calculate_chargeable_days(
    start_date: date, end_date: date, category: LeaveCategory, closed_holidays: List[date]
) -> Decimal:
    validate_category(category)
    if start_date > end_date:
        raise ValueError("Reversed date range")

    if category in (LeaveCategory.CL, LeaveCategory.RH, LeaveCategory.SCL):
        if closed_holidays is None:
            raise MissingLeaveFactsError("Closed-holiday data is required")

        holidays = set(closed_holidays)
        return Decimal(sum(
            1
            for ordinal in range(
                start_date.toordinal(), end_date.toordinal() + 1
            )
            if date.fromordinal(ordinal).weekday() < 5
            and date.fromordinal(ordinal) not in holidays
        ))
    elif category in (LeaveCategory.EL, LeaveCategory.VL):
        return Decimal((end_date - start_date).days + 1)
    elif category == LeaveCategory.COL:
        raise UnresolvedLeavePolicyError("COL counting rules are unconfirmed")
    else:
        raise ValueError(f"Unsupported leave category: {category}")

def validate_rh_date(
    requested_date: date, calendar: Optional[HolidayCalendar]
) -> None:
    if calendar is None:
        raise MissingLeaveFactsError("RH holiday calendar is missing")
    if not calendar.published:
        raise MissingLeaveFactsError("RH calendar is not published")
    if (
        calendar.effective_from is None
        or calendar.effective_to is None
        or calendar.holidays is None
    ):
        raise MissingLeaveFactsError(
            "RH calendar requires effective dates and holiday data"
        )
    if calendar.effective_from > calendar.effective_to:
        raise MissingLeaveFactsError("RH calendar effective range is invalid")
    if not calendar.effective_from <= requested_date <= calendar.effective_to:
        raise ValueError("RH date is outside the calendar effective range")
    if requested_date not in calendar.holidays:
        raise ValueError("RH date not listed in holidays")

def validate_faculty_vl_period(
    start_date: date, end_date: date, classification: str, vacation_periods: List[VacationPeriod]
) -> None:
    if not classification or not isinstance(classification, str):
        raise MissingLeaveFactsError("Employee classification is missing")
    if vacation_periods is None:
        raise MissingLeaveFactsError("Faculty vacation calendar is missing")
    if classification.strip().casefold() != "faculty":
        raise ValueError("VL period validation applies to faculty")
    if start_date > end_date:
        raise ValueError("Reversed VL date range")
    if not vacation_periods:
        raise MissingLeaveFactsError("Faculty vacation periods are missing")

    for period in vacation_periods:
        if period.start_date > period.end_date:
            raise MissingLeaveFactsError("Invalid vacation-period date range")
        if period.start_date <= start_date and end_date <= period.end_date:
            return
    raise ValueError("Faculty VL period outside any supplied vacation period")

def convert_unused_faculty_vl_to_el(unused_vl: Decimal) -> Decimal:
    if unused_vl < 0:
        raise ValueError("Negative unused VL")
    return unused_vl / Decimal("2")
