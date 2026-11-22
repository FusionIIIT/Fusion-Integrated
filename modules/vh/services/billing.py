# Billing and offline cash settlement services for VHMS.
import uuid
from datetime import date
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.vh.domain.cancellation import compute_cancellation_charge
from modules.vh.models.bill import Bill, BillLineItem, BillSettlement
from modules.vh.models.booking import Booking
from modules.vh.selectors.tariffs import get_applicable_tariff


@transaction.atomic
def generate_bill(booking_id: int, principal) -> Bill:
    # CFR-VH-011, BR-VH-023..037: Generates or updates bill preserving immutability if finalized.
    try:
        booking = Booking.objects.select_for_update().get(id=booking_id)
    except Booking.DoesNotExist:
        raise NotFoundError(f"Booking {booking_id} not found.") from None

    bill = Bill.objects.filter(booking=booking).first()
    if bill and bill.is_immutable:
        return bill

    bill_number = (
        bill.bill_number if bill else f"BILL-{date.today().year}-{uuid.uuid4().hex[:6].upper()}"
    )
    room_total = Decimal("0.00")
    meal_total = Decimal("0.00")
    cancellation_total = Decimal("0.00")
    line_items_data: list[dict] = []

    # 1. Room rent calculation
    allotments = booking.allotments.select_related("room").all()
    stay_days = max(1, (booking.departure_date - booking.arrival_date).days)
    one_day_room_total = Decimal("0.00")

    if allotments.exists():
        for allot in allotments:
            rate = get_applicable_tariff(
                category=booking.visitor_category,
                room_type=allot.room.room_type,
                occupancy=allot.occupancy_type,
                as_of_date=booking.arrival_date,
            )
            item_total = rate * Decimal(stay_days)
            one_day_room_total += rate
            if booking.status not in {"cancelled", "cancellation_requested"}:
                room_total += item_total
                rt = allot.room.room_type
                line_items_data.append(
                    {
                        "item_type": "room",
                        "description": f"Room {allot.room.room_number} ({rt}) x {stay_days} nights",
                        "quantity": Decimal(stay_days),
                        "unit_price": rate,
                        "total_price": item_total,
                    }
                )
    else:
        # Default tariff estimate for unallotted bookings
        rate = get_applicable_tariff(
            booking.visitor_category, "non_suite", "single", booking.arrival_date
        )
        one_day_room_total = rate * Decimal(booking.number_of_rooms)
        if booking.status not in {"cancelled", "cancellation_requested"}:
            room_total = one_day_room_total * Decimal(stay_days)
            nrooms = booking.number_of_rooms
            line_items_data.append(
                {
                    "item_type": "room",
                    "description": f"Estimated Room Rent ({nrooms} rooms) x {stay_days} nights",
                    "quantity": Decimal(stay_days),
                    "unit_price": one_day_room_total,
                    "total_price": room_total,
                }
            )

    # 2. Meal charges calculation
    meals = booking.meal_bookings.all()
    for m in meals:
        meal_total += m.amount
        desc = f"Meal {m.meal_option}"
        if m.individual_type:
            desc += f" ({m.individual_type})"
        if m.add_on_type:
            desc += f" ({m.add_on_type})"
        line_items_data.append(
            {
                "item_type": "meal",
                "description": f"{desc} on {m.meal_date}",
                "quantity": Decimal(m.quantity),
                "unit_price": m.rate,
                "total_price": m.amount,
            }
        )

    # 3. Cancellation charge calculation
    if booking.cancellation_charge_percentage > Decimal("0.00"):
        cancellation_total = compute_cancellation_charge(
            one_day_room_total, booking.cancellation_charge_percentage
        )
        cpct = booking.cancellation_charge_percentage
        line_items_data.append(
            {
                "item_type": "cancellation",
                "description": f"Cancellation Charge ({cpct}% of 1-day rent)",
                "quantity": Decimal("1.00"),
                "unit_price": cancellation_total,
                "total_price": cancellation_total,
            }
        )

    total_amount = room_total + meal_total + cancellation_total

    if not bill:
        bill = Bill.objects.create(
            booking=booking,
            bill_number=bill_number,
            visitor_category=booking.visitor_category,
            room_rent_total=room_total,
            meal_charge_total=meal_total,
            cancellation_charge_total=cancellation_total,
            total_amount=total_amount,
            billing_responsibility=booking.billing_responsibility,
            status="generated",
        )
    else:
        bill.room_rent_total = room_total
        bill.meal_charge_total = meal_total
        bill.cancellation_charge_total = cancellation_total
        bill.total_amount = total_amount
        bill.items.all().delete()
        bill.save()

    for item in line_items_data:
        BillLineItem.objects.create(
            bill=bill,
            item_type=item["item_type"],
            description=item["description"],
            quantity=item["quantity"],
            unit_price=item["unit_price"],
            total_price=item["total_price"],
        )

    return bill


@transaction.atomic
def record_offline_settlement(
    bill_id: int,
    amount_paid: Decimal,
    receipt_number: str,
    notes: str,
    principal,
) -> BillSettlement:
    # CFR-VH-011, BR-VH-036, BR-VH-037: Records offline cash settlement and freezes bill.
    try:
        bill = Bill.objects.select_for_update().get(id=bill_id)
    except Bill.DoesNotExist:
        raise NotFoundError(f"Bill {bill_id} not found.") from None

    if bill.status == "settled":
        raise ConflictError(f"Bill {bill.bill_number} has already been settled.")

    if amount_paid <= Decimal("0.00"):
        raise BadRequestError("Settlement amount must be greater than zero.")

    caretaker_id = getattr(principal, "user_id", 0)
    settlement = BillSettlement.objects.create(
        bill=bill,
        payment_mode="offline_cash",
        amount_paid=amount_paid,
        settled_by=caretaker_id,
        receipt_number=receipt_number.strip(),
        notes=notes.strip(),
    )

    bill.status = "settled"
    bill.is_immutable = True
    bill.finalized_at = timezone.now()
    bill.save()
    return settlement


@transaction.atomic
def record_bill_verification(booking_id: int, verified: bool, principal) -> Bill:
    # AFR-VH-065: Records guest bill verification during checkout.
    try:
        bill = Bill.objects.select_for_update().get(booking_id=booking_id)
    except Bill.DoesNotExist:
        bill = generate_bill(booking_id, principal)

    if verified:
        bill.status = "verified" if bill.status != "settled" else "settled"
        bill.verified_by = getattr(principal, "user_id", 0)
        bill.verified_at = timezone.now()
        bill.save()
    return bill
