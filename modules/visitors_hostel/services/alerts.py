"""Idempotent date-based no-show and overstay alert generation."""
from django.db import IntegrityError, transaction
from django.utils import timezone
from datetime import datetime, time

from modules.visitors_hostel.models import (
    Booking, OperationalRoleAssignment, StayAlert, Tariff)
from modules.visitors_hostel.domain.rules import cancellation_charge
from modules.visitors_hostel.services import notifications


@transaction.atomic
def generate_stay_alerts(*, today=None):
    today = today or timezone.localdate()
    caretaker = OperationalRoleAssignment.objects.filter(
        role="caretaker", ends_at__isnull=True).values_list("user_id", flat=True).first()
    if caretaker is None:
        return 0
    generated = 0
    now = timezone.localtime()
    no_show_rows = Booking.objects.filter(
        status__in=["approved", "room_allotted"], arrival_date__lte=today)
    overstay_rows = Booking.objects.filter(status="checked_in", departure_date__lte=today)
    for kind, rows in (("no_show", no_show_rows), ("overstay", overstay_rows)):
        for booking in rows:
            if kind == "no_show":
                due = timezone.make_aware(datetime.combine(
                    booking.arrival_date,
                    booking.arrival_time or time.max.replace(microsecond=0)))
            else:
                due = timezone.make_aware(datetime.combine(
                    booking.departure_date,
                    booking.departure_time or time.max.replace(microsecond=0)))
            if now <= due:
                continue
            try:
                with transaction.atomic():
                    alert = StayAlert.objects.create(booking=booking, kind=kind)
            except IntegrityError:
                continue
            if kind == "no_show" and booking.cancellation_charge == 0:
                tariff = Tariff.objects.filter(
                    occupancy=booking.requested_occupancy,
                    visitor_category=booking.visitor_category,
                    effective_from__lte=booking.arrival_date, active=True,
                ).order_by("-effective_from").first()
                if tariff:
                    booking.cancellation_charge = cancellation_charge(
                        arrival_date=booking.arrival_date, cancellation_date=booking.arrival_date,
                        one_day_room_rent=tariff.daily_rate * booking.room_count,
                        no_show=True)
                    booking.save(update_fields=["cancellation_charge", "updated_at"])
            notifications.enqueue(
                topic="stay.no_show" if kind == "no_show" else "stay.overstay",
                dedupe_key=f"stay-alert:{booking.pk}:{kind}",
                subject=f"VH {kind.replace('_', ' ')} alert: {booking.booking_number}",
                body=(f"Booking {booking.booking_number} has a {kind.replace('_', ' ')} "
                      f"exception."),
                user_id=caretaker,
                payload={"booking_id": booking.pk, "alert_id": alert.pk})
            generated += 1
    return generated
