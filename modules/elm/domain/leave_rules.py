"""Pure business rules for ELM leave calculations and validation."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

CONTINUOUS_DAY_CATEGORIES = {"EL", "COL", "VL"}
SUPPORTED_CATEGORIES = {"CL", "RH", "SCL", "EL", "COL", "VL"}

ANNUAL_ENTITLEMENTS = {
    "CL": Decimal("8"),
    "RH": Decimal("2"),
    "SCL": Decimal("15"),
    "EL": Decimal("30"),
    "COL": Decimal("20"),
    "VL": Decimal("60"),
}


@dataclass(frozen=True)
class LeavePeriod:
    start_date: date
    end_date: date
    category: str

    def validate(self) -> None:
        if self.category not in SUPPORTED_CATEGORIES:
            raise ValueError("Unsupported leave category.")
        if self.end_date < self.start_date:
            raise ValueError("End date cannot be before start date.")

    @property
    def calendar_days(self) -> int:
        self.validate()
        return (self.end_date - self.start_date).days + 1


def annual_entitlement(category: str) -> Decimal:
    """Return baseline annual entitlement for a supported leave category."""
    if category not in ANNUAL_ENTITLEMENTS:
        raise ValueError("Unsupported leave category.")
    return ANNUAL_ENTITLEMENTS[category]


def count_leave_days(
    start_date: date,
    end_date: date,
    category: str,
) -> Decimal:
    """Count calendar days for continuous leave categories.

    CL, RH, and SCL require category-specific counting and are deliberately
    not calculated by this continuous-day helper.
    """
    period = LeavePeriod(start_date, end_date, category)
    period.validate()

    if category not in CONTINUOUS_DAY_CATEGORIES:
        raise ValueError(
            f"{category} does not use continuous calendar-day counting."
        )

    return Decimal(period.calendar_days)


def validate_no_overlap(
    start_date: date,
    end_date: date,
    existing_periods: list[tuple[date, date]],
) -> None:
    """Reject a date-range overlap with an existing active leave period."""
    if end_date < start_date:
        raise ValueError("End date cannot be before start date.")

    for existing_start, existing_end in existing_periods:
        if start_date <= existing_end and existing_start <= end_date:
            raise ValueError("Leave overlaps an existing active leave period.")


def convert_vacation_leave_to_earned_leave(
    unused_vl_days: Decimal,
) -> Decimal:
    """Convert unused VL to EL at the required 2:1 ratio."""
    unused_vl_days = Decimal(unused_vl_days)

    if unused_vl_days < 0:
        raise ValueError("Unused VL balance cannot be negative.")

    return unused_vl_days / Decimal("2")
