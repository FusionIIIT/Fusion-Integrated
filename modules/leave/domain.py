"""Pure ELM arithmetic and validation helpers."""

from datetime import timedelta
from decimal import Decimal

CATEGORIES = ("CL", "RH", "SCL", "EL", "COL", "VL")
CONTINUOUS = {"EL", "COL", "VL"}
ENTITLEMENTS = {
    "CL": Decimal("8"),
    "RH": Decimal("2"),
    "SCL": Decimal("15"),
    "EL": Decimal("30"),
    "COL": Decimal("20"),
    "VL": Decimal("60"),
}


class LeaveRuleError(ValueError):
    pass


def chargeable_days(category, start, end, *, half=None, closed_holidays=()):
    if end < start:
        raise LeaveRuleError("Leave end date must not precede its start date.")
    if category == "CL" and half in {"first", "second"}:
        return Decimal("0.5")
    days = (end - start).days + 1
    if category in CONTINUOUS:
        return Decimal(days)
    return Decimal(
        sum(
            1
            for i in range(days)
            if (start + timedelta(days=i)).weekday() < 5
            and start + timedelta(days=i) not in set(closed_holidays)
        )
    )


def overlaps(start, end, category, half, other_start, other_end, other_category, other_half):
    if category == other_category == "CL" and start == end == other_start == other_end:
        return {half, other_half} != {"first", "second"}
    return start <= other_end and other_start <= end


def conversion_vl_to_el(vl_balance):
    return (Decimal(vl_balance) / Decimal("2")).quantize(Decimal("0.01"))
