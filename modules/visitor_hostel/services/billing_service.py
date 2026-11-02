from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from modules.visitor_hostel.models import BookingDetail, Bill, Tariff, MealBooking
from modules.visitor_hostel.domain.cancellation_policy import calculate_cancellation_charge
from modules.visitor_hostel.domain.tariff_policy import get_applicable_tariff, calculate_room_charge

@transaction.atomic
def generate_bill_for_booking(booking_id: str) -> Bill:
    booking = BookingDetail.objects.get(booking_id=booking_id)
    
    days = max(1, (booking.booking_to  - booking.booking_from).days)
    room_charges = Decimal("500.00") * days
    meal_charges = sum(MealBooking.objects.filter(booking=booking).values_list('amount', flat=True)) or Decimal("0.00")
    
    if booking.status == 'CANCELLED':
        cancellation_charges = calculate_cancellation_charge(booking.booking_from, timezone.now().date(), Decimal("500.00"))
    else:
        cancellation_charges = Decimal("0.00")
    
    total = room_charges + meal_charges + cancellation_charges
    
    bill, _ = Bill.objects.update_or_create(
        booking=booking,
        defaults={
            'bill_number': f"BILL-{booking.booking_id}",
            'room_charges': room_charges,
            'meal_charges': meal_charges,
            'cancellation_charges': cancellation_charges,
            'total_amount': total,
            'settlement_status': 'Pending',
            'is_immutable': False,
        }
    )
    
    return bill

@transaction.atomic
def settle_cash_bill(bill_number: str, actor: str, amount_paid: Decimal) -> Bill:
    bill = Bill.objects.get(bill_number=bill_number)
    
    if bill.is_immutable:
        raise ValueError("Finalized bill is immutable and cannot be re-settled.")
    
    bill.settlement_status = 'Settled'
    bill.payment_mode = 'Cash'
    bill.settled_at = timezone.now()
    bill.settled_by = actor
    bill.is_immutable = True
    bill.save()
    
    return bill
