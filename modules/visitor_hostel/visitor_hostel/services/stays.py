"""Time-triggered work (UC-VH-024): no-show and overstay alerts, reminders.

Alerts are records for the Caretaker (BR-VH-017/018); the PS asks for emails
only for check-in and check-out reminders (AFR-VH-079). Both passes are
idempotent, so a missed or doubled beat tick is harmless.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, time, timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone

from modules.visitor_hostel.domain import state_machine as sm
from modules.visitor_hostel.models import Booking, StayAlert
from modules.visitor_hostel.services import notifications

log = logging.getLogger("fusion.visitor_hostel.stays")

#: With no recorded time, the whole day counts.
_END_OF_DAY = time(23, 59, 59)


def expected(day: date, at: time | None) -> datetime:
    return timezone.make_aware(datetime.combine(day, at or _END_OF_DAY))


def _alert(booking: Booking, kind: str, when: datetime) -> bool:
    try:
        with transaction.atomic():
            StayAlert.objects.create(booking=booking, kind=kind, expected_at=when)
    except IntegrityError:
        return False
    return True


def scan(now: datetime | None = None) -> dict:
    now = now or timezone.now()
    today = timezone.localdate(now)
    raised = {"no_show": 0, "overstay": 0}

    # BR-VH-017: not checked in by the recorded arrival.
    for b in Booking.objects.filter(status__in=(sm.APPROVED, sm.ROOM_ALLOTTED),
                                    arrival_date__lte=today):
        when = expected(b.arrival_date, b.arrival_time)
        if now > when and _alert(b, StayAlert.NO_SHOW, when):
            raised["no_show"] += 1

    # BR-VH-018: still checked in past the approved departure.
    for b in Booking.objects.filter(status=sm.CHECKED_IN, departure_date__lte=today):
        when = expected(b.departure_date, b.departure_time)
        if now > when and _alert(b, StayAlert.OVERSTAY, when):
            raised["overstay"] += 1

    if any(raised.values()):
        log.info("visitor_hostel.stays.alerts %s", raised)
    return raised


@transaction.atomic
def send_reminders(today: date | None = None) -> dict:
    """Arrivals tomorrow and departures today, to the Indenter."""
    today = today or timezone.localdate()
    sent = {"checkin": 0, "checkout": 0}
    for b in Booking.objects.filter(status__in=(sm.APPROVED, sm.ROOM_ALLOTTED),
                                    arrival_date=today + timedelta(days=1)):
        if notifications.enqueue(
                topic="stay.checkin_reminder",
                dedupe_key=f"vh:checkin_reminder:{b.pk}:{b.arrival_date}",
                recipient_user_id=b.indenter_user_id,
                subject=f"Visitor arriving tomorrow — booking #{b.pk}",
                body=f"{b.visitor_name} is due at the Visitors Hostel on "
                     f"{b.arrival_date:%d %b %Y}.",
                payload={"booking_id": b.pk}):
            sent["checkin"] += 1
    for b in Booking.objects.filter(status=sm.CHECKED_IN, departure_date=today):
        if notifications.enqueue(
                topic="stay.checkout_reminder",
                dedupe_key=f"vh:checkout_reminder:{b.pk}:{b.departure_date}",
                recipient_user_id=b.indenter_user_id,
                subject=f"Visitor checking out today — booking #{b.pk}",
                body=f"{b.visitor_name} is due to check out of the Visitors Hostel "
                     f"today.",
                payload={"booking_id": b.pk}):
            sent["checkout"] += 1
    return sent
