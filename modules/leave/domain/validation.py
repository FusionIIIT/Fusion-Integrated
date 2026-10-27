"""Leave request validation rules.

Pure Python domain logic following BR-EL-034 and related validation rules.
No Django/DRF imports here.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass
class ValidationResult:
    """Result of validation check."""
    is_valid: bool
    errors: list[str]
    warnings: list[str]


class LeaveRequestValidator:
    """Validation rules for leave requests."""

    # BR-EL-011: Continuous-day counting
    MIN_DURATION = 1
    MAX_DURATION = 30  # Maximum continuous leave days

    # BR-EL-012: Applicant non-overlap with half-day CL exception
    MIN_GAP_FOR_HALF_DAY = 1

    # BR-EL-034: No post-submission modification
    DRAFT_ONLY_MODIFICATION = True

    # Minimum date difference for valid dates
    MIN_DATE_DIFF_DAYS = 1

    def __init__(self, request_data: dict):
        """Initialize validator with request data."""
        self.request_data = request_data

    def validate_dates(self, start_date: date, end_date: date) -> ValidationResult:
        """Validate date range."""
        errors = []
        warnings = []

        if not start_date or not end_date:
            errors.append("Both start_date and end_date are required")
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings)

        if start_date > end_date:
            errors.append("Start date must be before or equal to end date")
        elif start_date == end_date:
            warnings.append("Start and end date are the same - consider using a single day")

        # Check for continuous days (BR-EL-011)
        days_between = (end_date - start_date).days + 1
        if days_between < self.MIN_DURATION:
            errors.append(f"Leave duration must be at least {self.MIN_DURATION} day(s)")
        elif days_between > self.MAX_DURATION:
            warnings.append(f"Leave duration of {days_between} days exceeds maximum of {self.MAX_DURATION} days")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    def validate_leave_category(self, category: str) -> ValidationResult:
        """Validate leave category."""
        errors = []
        warnings = []

        valid_categories = ["CL", "RH", "SCL", "EL", "COL", "VL"]
        if category not in valid_categories:
            errors.append(f"Invalid leave category: {category}. Must be one of: {valid_categories}")

        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)

    def validate_scl_authority(self, kind: str) -> ValidationResult:
        """Validate SCL authority (BR-EL-004)."""
        errors = []
        warnings = []

        if kind == "staff" and self.request_data.get("category") == "SCL":
            errors.append("Staff members cannot apply for Special Casual Leave")

        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)

    def validate_station_leave(self, category: str) -> ValidationResult:
        """Validate Station Leave coupling (BR-EL-013)."""
        errors = []
        warnings = []

        if self.request_data.get("station_leave"):
            if category not in ["CL", "RH"]:
                errors.append("Station Leave is only applicable to CL and RH")

        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)

    def validate_non_overlap(self, half_day_leaves: list[date]) -> ValidationResult:
        """Validate non-overlap with half-day CL (BR-EL-012)."""
        errors = []
        warnings = []

        if not half_day_leaves:
            return ValidationResult(is_valid=True, errors=errors, warnings=warnings)

        for half_day_date in half_day_leaves:
            if self.request_data.get("start_date", date.today()) >= half_day_date:
                errors.append(f"Leave overlaps with half-day CL on {half_day_date}")

        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)

    def validate_no_post_submission_modification(self, is_draft: bool) -> ValidationResult:
        """BR-EL-034: No post-submission modification."""
        errors = []
        warnings = []

        if not is_draft and self.request_data.get("status") != "draft":
            errors.append("Cannot modify leave request after submission")
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings)

        return ValidationResult(is_valid=True, errors=errors, warnings=warnings)

    def validate_duration_calculation(self, start_date: date, end_date: date, category: str) -> ValidationResult:
        """Validate duration calculation based on category."""
        errors = []
        warnings = []

        days = (end_date - start_date).days + 1

        if category == "CL" or category == "RH":
            # Half-day treatment applies
            if days > 1:
                warnings.append(f"Half-day CL treatment will apply for {days} days")

        return ValidationResult(is_valid=True, errors=errors, warnings=warnings)

    def validate_all(self, **kwargs) -> ValidationResult:
        """Run all validation checks."""
        errors = []
        warnings = []

        # Extract parameters
        category = kwargs.get("category")
        start_date = kwargs.get("start_date")
        end_date = kwargs.get("end_date")
        kind = kwargs.get("kind")
        station_leave = kwargs.get("station_leave", False)
        half_day_leaves = kwargs.get("half_day_leaves", [])
        is_draft = kwargs.get("is_draft", True)

        # Run validation checks
        errors.extend([e for e in self.validate_dates(start_date, end_date).errors])
        errors.extend([e for e in self.validate_leave_category(category).errors])

        if category == "SCL":
            errors.extend([e for e in self.validate_scl_authority(kind).errors])

        errors.extend([e for e in self.validate_station_leave(station_leave).errors])
        errors.extend([e for e in self.validate_non_overlap(half_day_leaves).errors])
        errors.extend([e for e in self.validate_no_post_submission_modification(is_draft).errors])

        if start_date and end_date:
            errors.extend([e for e in self.validate_duration_calculation(start_date, end_date, category).errors])

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=[w for w in self.validate_dates(start_date, end_date).warnings]
        )


def validate_leave_request(
    category: str,
    start_date: date,
    end_date: date,
    kind: str,
    station_leave: bool = False,
    half_day_leaves: list[date] = [],
    is_draft: bool = True,
) -> ValidationResult:
    """Validate a leave request."""
    validator = LeaveRequestValidator({})
    return validator.validate_all(
        category=category,
        start_date=start_date,
        end_date=end_date,
        kind=kind,
        station_leave=station_leave,
        half_day_leaves=half_day_leaves,
        is_draft=is_draft,
    )


def get_error_message(error: str) -> str:
    """Convert error to user-friendly message."""
    error_messages = {
        "Invalid leave category": "Please select a valid leave category",
        "Start date must be before or equal to end date": "Start date cannot be after end date",
        "Leave duration must be at least 1 day(s)": "Leave must be for at least one day",
        "Staff members cannot apply for Special Casual Leave": "Staff members cannot apply for SCL",
        "Station Leave is only applicable to CL and RH": "Station Leave is only for CL and RH",
        "Cannot modify leave request after submission": "Leave requests cannot be modified after submission",
        "Leave duration exceeds maximum": "Leave duration exceeds the maximum allowed",
    }
    return error_messages.get(error, error)
