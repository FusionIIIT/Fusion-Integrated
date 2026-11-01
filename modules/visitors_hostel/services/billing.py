from decimal import Decimal

from django.db import transaction

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.visitors_hostel.models import Bill, Booking, CashSettlement


def generate_bill(*, booking_id, actor):
    if not actor.has_permission("visitor_hostel.bill.manage"):
        raise PermissionDeniedError()
    booking = Booking.objects.filter(pk=booking_id).first()
    if booking is None:
        raise NotFoundError("No such booking.")
    lines = []
    tariff_snapshot = {"allocations": []}
    for allocation in booking.allocations.select_related("room"):
        nights = (allocation.departure_date - allocation.arrival_date).days
        amount = allocation.tariff_daily_snapshot * nights
        lines.append({"kind": "room", "description": f"Room {allocation.room.room_number}",
                      "quantity": nights, "unit_rate": str(allocation.tariff_daily_snapshot),
                      "amount": str(amount)})
        tariff_snapshot["allocations"].append({"room_id": allocation.room_id,
            "daily_rate": str(allocation.tariff_daily_snapshot), "nights": nights})
    for meal in booking.meal_bookings.all():
        amount = meal.unit_rate * meal.quantity
        lines.append({"kind": "meal", "description": ", ".join(meal.options + meal.add_ons),
                      "date": meal.meal_date.isoformat(), "quantity": meal.quantity,
                      "unit_rate": str(meal.unit_rate), "amount": str(amount)})
    if booking.cancellation_charge:
        lines.append({"kind": "cancellation", "description": "Cancellation charge",
                      "quantity": 1, "unit_rate": str(booking.cancellation_charge),
                      "amount": str(booking.cancellation_charge)})
    total = sum((Decimal(line["amount"]) for line in lines), Decimal("0.00"))
    return Bill.objects.create(
        booking=booking, bill_number=f"VHB-{booking.booking_number}-{Bill.objects.filter(booking=booking).count()+1:02d}",
        generated_by_user_id=getattr(actor, "user_id", None),
        tariff_snapshot=tariff_snapshot, line_items=lines,
        total_amount=total, billing_responsibility=booking.billing_responsibility)


@transaction.atomic
def record_cash_settlement(*, bill_id, actor, amount, reference_note=""):
    if not actor.has_permission("visitor_hostel.bill.manage"):
        raise PermissionDeniedError()
    bill = Bill.objects.select_for_update().filter(pk=bill_id).first()
    if bill is None:
        raise NotFoundError("No such bill.")
    paid = sum(bill.settlements.values_list("amount", flat=True), Decimal("0.00"))
    amount = Decimal(str(amount))
    if amount <= 0 or paid + amount > bill.total_amount:
        raise ConflictError("Settlement must be positive and cannot exceed the balance.",
                            code="invalid_settlement")
    return CashSettlement.objects.create(
        bill=bill, amount=amount,
        received_by_user_id=actor.user_id, reference_note=reference_note)
