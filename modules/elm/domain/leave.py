"""Pure value helpers for ELM; kept independent of Django/DRF."""
from datetime import date
from decimal import Decimal

SUPPORTED_CATEGORIES = ("CL", "RH", "SCL", "EL", "VL", "COL")


def inclusive_calendar_days(start: date, end: date) -> int:
    if end < start:
        raise ValueError("end_date must not precede start_date")
    return (end - start).days + 1


def validate_category(category: str) -> str:
    value = category.upper()
    if value not in SUPPORTED_CATEGORIES:
        raise ValueError("Unsupported leave category")
    return value


def available_balance(opening: Decimal, credited: Decimal, adjusted: Decimal, consumed: Decimal) -> Decimal:
    return opening + credited + adjusted - consumed
