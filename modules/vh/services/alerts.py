# Exception and stay alert evaluation services for VHMS.
from datetime import date

from django.db import transaction

from modules.vh.models.alerts import StayAlert
from modules.vh.models.booking import Booking


@transaction.atomic
def evaluate_no_shows() -> int:
    # CFR-VH-008, BR-VH-017, UC-VH-024: Detects bookings where guest did not check in on arrival.
    today = date.today()
    overdue_bookings = Booking.objects.filter(
        arrival_date__lt=today,
        status="room_allotted",
        checkin_time__isnull=True,
    )
    alert_count = 0
    for b in overdue_bookings:
        exists = StayAlert.objects.filter(booking=b, alert_type="no_show", status="active").exists()
        if not exists:
            StayAlert.objects.create(
                booking=b,
                alert_type="no_show",
                status="active",
                details=f"Expected check-in on {b.arrival_date} did not occur.",
            )
            alert_count += 1
    return alert_count


@transaction.atomic
def evaluate_overstays() -> int:
    # CFR-VH-008, BR-VH-018, UC-VH-024: Detects guests overstaying beyond approved departure date.
    today = date.today()
    overstay_bookings = Booking.objects.filter(
        departure_date__lt=today,
        status="checked_in",
        checkout_time__isnull=True,
    )
    alert_count = 0
    for b in overstay_bookings:
        exists = StayAlert.objects.filter(
            booking=b, alert_type="overstay", status="active"
        ).exists()
        if not exists:
            StayAlert.objects.create(
                booking=b,
                alert_type="overstay",
                status="active",
                details=f"Approved departure date {b.departure_date} exceeded without checkout.",
            )
            alert_count += 1
    return alert_count
