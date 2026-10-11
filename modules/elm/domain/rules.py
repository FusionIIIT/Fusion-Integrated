from datetime import date, timedelta
from decimal import Decimal

CATEGORIES = ("CL", "RH", "SCL", "EL", "COL", "VL")
CONTINUOUS = frozenset(("EL", "COL", "VL"))
PENDING = frozenset(("substitute", "applicant_action", "unit_head", "establishment", "sanction"))
AUTHORITY_ROLES = ("Deputy Registrar (Estt.)", "Dean", "Registrar", "Director")


class RuleViolation(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def dates(start, end):
    if start > end or (end - start).days > 3660:
        raise RuleViolation("invalid_period", "Enter a valid leave period of at most ten years.")
    return [start + timedelta(days=n) for n in range((end - start).days + 1)]


def count_days(category, start, end, half, calendars, weekdays):
    # BR-EL-003, BR-EL-010, BR-EL-011, BR-EL-031.
    if category not in CATEGORIES:
        raise RuleViolation("invalid_category", "Choose CL, RH, SCL, EL, COL, or VL.")
    if half != "full" and (category != "CL" or start != end):
        raise RuleViolation("invalid_half", "Only single-date CL supports a half day.")
    result = {}
    for day in dates(start, end):
        calendar = calendars.get(day.year)
        if calendar is None:
            raise RuleViolation("calendar_missing", f"Publish the holiday/RH calendar for {day.year}.")
        closed = day.weekday() in weekdays or day.isoformat() in calendar["holidays"]
        if category == "RH" and day.isoformat() not in calendar["restricted_holidays"]:
            raise RuleViolation("invalid_rh", "Every requested RH date must be a published restricted holiday.")
        if category in CONTINUOUS or category == "RH" or not closed:
            amount = Decimal("1") if half == "full" else Decimal("0.5")
            result[day.year] = result.get(day.year, Decimal("0")) + amount
    if not result:
        raise RuleViolation("no_leave_days", "The period contains no chargeable leave days.")
    return result


def overlaps(start, end, half, other_start, other_end, other_half):
    # BR-EL-012: opposite CL halves are the only interval overlap exception.
    if start > other_end or end < other_start:
        return False
    return not (start == end == other_start == other_end
                and {half, other_half} == {"first", "second"})


def entitlements(kind):
    # BR-EL-002–009.
    return {"CL": Decimal("8"), "RH": Decimal("2"), "SCL": Decimal("15"),
            "EL": Decimal("30") if kind == "staff" else Decimal("0"),
            "COL": Decimal("20"), "VL": Decimal("60") if kind == "faculty" else Decimal("0")}


def allowed_decisions(stage, category, request_kind):
    if stage == "substitute":
        return ("accept", "decline")
    if stage == "unit_head" and category not in ("CL", "RH"):
        return ("recommend", "not_recommend")
    if stage == "establishment":
        return ("forward",)
    if stage == "sanction" and request_kind == "resumption":
        return ("review",)
    if stage in ("unit_head", "sanction"):
        return ("approve", "reject")
    return ()
