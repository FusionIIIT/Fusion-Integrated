# Pure Python cancellation charge calculation per BR-VH-006 through BR-VH-009.
from datetime import date
from decimal import Decimal


def compute_cancellation_percentage(arrival_date: date, request_date: date) -> Decimal:
    # BR-VH-006..009: 0% if >= 7 days, 25% if 1..6 days, 50% if same day.
    days_before = (arrival_date - request_date).days
    if days_before > 7:
        return Decimal("0.00")
    if days_before == 7:
        return Decimal("0.00")
    if 1 <= days_before < 7:
        return Decimal("25.00")
    # Same day (days_before == 0) or past arrival / no-show
    return Decimal("50.00")


def compute_cancellation_charge(one_day_rent: Decimal, percentage: Decimal) -> Decimal:
    # Computes total cancellation charge based on one-day room rent.
    if one_day_rent <= Decimal("0.00") or percentage <= Decimal("0.00"):
        return Decimal("0.00")
    charge = (one_day_rent * percentage) / Decimal("100.00")
    return charge.quantize(Decimal("0.01"))
