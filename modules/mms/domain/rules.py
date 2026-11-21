"""Pure MMS input and state-transition rules."""
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError


def validate_rebate(*, reason: str, explanation: str, starts_on: date,
                    ends_on: date, today: date) -> None:
    allowed = {"medical", "institute_leave", "family_function", "other"}
    if reason not in allowed:
        raise ValidationError({"reason": "Select a supported rebate reason."})
    if reason == "other" and not explanation.strip():
        raise ValidationError({"explanation": "An explanation is required for Other."})
    if ends_on < starts_on:
        raise ValidationError({"ends_on": "End date must be on or after start date."})
    if (ends_on - starts_on).days + 1 < 3:
        raise ValidationError({"ends_on": "A rebate must cover at least three days."})
    if starts_on < today + timedelta(days=1):
        raise ValidationError({"starts_on": "Submit at least one calendar day in advance."})


def validate_special_food(*, requested_for: date, today: date) -> None:
    if requested_for < today + timedelta(days=1):
        raise ValidationError(
            {"requested_for": "Submit at least one calendar day in advance."})


def next_local_midnight(now: datetime, tz) -> datetime:
    next_day = now.astimezone(tz).date() + timedelta(days=1)
    return datetime.combine(next_day, time.min, tzinfo=tz)


def calculate_bill(*, daily_rate: Decimal, served_days: int,
                   special_food_charges: Decimal,
                   rebate_deduction: Decimal) -> Decimal:
    gross = daily_rate * served_days + special_food_charges - rebate_deduction
    return gross.quantize(Decimal("0.01"))
