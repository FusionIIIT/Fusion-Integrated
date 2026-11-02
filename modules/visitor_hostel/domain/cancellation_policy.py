from datetime import date, datetime
from decimal import Decimal
from typing import Union

def calculate_cancellation_charge(arrival_date: Union[date, str], cancel_date: Union[date, str], one_day_room_rent: Decimal = Decimal("0.00")) -> Decimal:
    if isinstance(arrival_date, str):
        arrival_date = datetime.strptime(arrival_date, '%Y-%m-%d').date()
    if isinstance(cancel_date, str):
        cancel_date = datetime.strptime(cancel_date, '%Y-%m-%d').date()
    days_before = (arrival_date - cancel_date).days
    if days_before >= 7:
        return Decimal("0.00")
    elif 0 < days_before < 7:
        return (one_day_room_rent * Decimal("0.25")).quantize(Decimal("0.01"))
    else:
        return (one_day_room_rent * Decimal("0.50")).quantize(Decimal("0.01"))

def calculate_refund_amount(total_paid: Decimal, cancellation_charge: Decimal) -> Decimal:
    refund = total_paid - cancellation_charge
    return max(Decimal("0.00"), refund)
