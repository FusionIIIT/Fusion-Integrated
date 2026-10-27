"""Leave entitlements and calculation rules (BR-EL-001..012)."""
from __future__ import annotations

import datetime

ENTITLEMENT = {
    "CL": 8.0,
    "RH": 2.0,
    "SCL": 15.0,
    "EL": 30.0,
    "COL": 20.0,
    "VL": 60.0,
}

# Categories that carry forward to next calendar year
CARRY_FORWARD = frozenset({"EL", "COL"})

# Categories where intervening weekends/holidays count continuously (BR-EL-011)
CONTINUOUS_COUNTING = frozenset({"EL", "COL", "VL"})


class OverlapError(Exception):
    def __init__(self, message: str = "Requested leave dates overlap with an existing leave request."):
        super().__init__(message)
        self.message = message


class InsufficientBalanceError(Exception):
    def __init__(self, category: str, requested: float, available: float):
        super().__init__(
            f"Insufficient leave balance for {category}: requested {requested} days, available {available} days."
        )
        self.category = category
        self.requested = requested
        self.available = available


def yearly_credit(category: str) -> float:
    return ENTITLEMENT.get(category, 0.0)


def carries_forward(category: str) -> bool:
    return category in CARRY_FORWARD


def vl_to_el(vl_left: float) -> float:
    """VL to EL year-end conversion: 50% of unutilized VL converts to EL (BR-EL-007)."""
    return max(0.0, vl_left / 2.0)


def is_continuous(category: str) -> bool:
    return category in CONTINUOUS_COUNTING


def calculate_days(category: str, start: datetime.date, end: datetime.date, half_day: bool = False) -> float:
    """Calculate the debit days for a leave span respecting BR-EL-010 and BR-EL-011."""
    if start > end:
        return 0.0

    if half_day and category == "CL":
        return 0.5

    if is_continuous(category):
        return float((end - start).days + 1)

    # For non-continuous (CL, RH, SCL): exclude Saturdays (5) and Sundays (6)
    cur = start
    work_days = 0
    while cur <= end:
        if cur.weekday() < 5:
            work_days += 1
        cur += datetime.timedelta(days=1)
    return float(max(1, work_days))


def validate_non_overlap(existing_requests, new_start: datetime.date, new_end: datetime.date,
                         new_half_day: bool = False, new_period: str = "none") -> None:
    """Enforce applicant non-overlap constraint with half-day CL exception (BR-EL-012)."""
    for req in existing_requests:
        # Ignore terminal states
        if req.status in ("rejected", "withdrawn", "cancelled"):
            continue

        # Overlap occurs if start <= req.end_date and end >= req.start_date
        if new_start <= req.end_date and new_end >= req.start_date:
            # Check for the half-day CL exception on the exact same date
            if (new_start == new_end == req.start_date == req.end_date and
                    req.category == "CL" and new_half_day and req.half_day):
                req_period = getattr(req, "half_day_period", "none")
                if new_period in ("FN", "AN") and req_period in ("FN", "AN") and new_period != req_period:
                    continue  # Valid non-conflicting half-day split!
            raise OverlapError(
                f"Dates {new_start} to {new_end} overlap with existing leave #{req.pk} ({req.status})."
            )
