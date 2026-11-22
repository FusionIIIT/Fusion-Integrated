"""Transactional booking operations. Callers hold a lock on the booking row.

Room rows are locked in id order before availability checks. PostgreSQL is
required for concurrent production writes; SQLite is for fast unit tests only.
"""

from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from .models import AuditEvent, Bill, Room, RoomAllotment, VisitorCategoryTariff


def audit(booking, principal, action, **details):
    entry = AuditEvent.objects.create(
        booking=booking, actor_id=principal.user_id, action=action, details=details
    )

    if booking:
        queue_notification(
            action,
            key=f"booking-event:{entry.pk}",
            booking=booking,
            role="vh_in_charge" if action == "forwarded" else "vh_caretaker",
            **details,
        )
        if booking.indenter_id is not None:
            queue_notification(
                action,
                key=f"booking-event:{entry.pk}:requester",
                booking=booking,
                recipient_id=booking.indenter_id,
                **details,
            )


def require_state(booking, *states):
    if booking.status not in states:
        raise ValidationError({"status": "This operation is not allowed in the current state."})


def arrival(booking):
    return timezone.make_aware(datetime.combine(booking.check_in_date, booking.check_in_time))


def departure(booking):
    return timezone.make_aware(datetime.combine(booking.check_out_date, booking.check_out_time))


def before_arrival(booking):
    if timezone.now() >= arrival(booking):
        raise ValidationError("Requests must be submitted before arrival.")


def tariff_for(booking):
    tariff = (
        VisitorCategoryTariff.objects.filter(
            category=booking.visitor_category,
            room_type=booking.room_type,
            occupancy=booking.occupancy,
            effective_from__lte=booking.check_in_date,
        )
        .order_by("-effective_from", "-pk")
        .first()
    )
    if tariff is None:
        raise ValidationError("No applicable tariff is configured for this stay.")
    return tariff.daily_rate


def available_rooms(booking):
    conflicts = (
        RoomAllotment.objects.filter(
            booking__status__in=("approved", "confirmed", "checked_in"),
            booking__check_in_date__lte=booking.check_out_date,
            booking__check_out_date__gte=booking.check_in_date,
        )
        .exclude(booking=booking)
        .filter(
            (
                Q(booking__check_in_date__lt=booking.check_out_date)
                | Q(booking__check_in_time__lt=booking.check_out_time)
            ),
            (
                Q(booking__check_out_date__gt=booking.check_in_date)
                | Q(booking__check_out_time__gt=booking.check_in_time)
            ),
        )
    )
    return (
        Room.objects.filter(room_type=booking.room_type)
        .exclude(status="maintenance")
        .exclude(pk__in=conflicts.values("room_id"))
    )


def allot(booking, room_ids):
    require_state(booking, "approved")
    if len(room_ids) != booking.number_of_rooms or len(set(room_ids)) != len(room_ids):
        raise ValidationError("Provide exactly the requested number of distinct rooms.")
    rooms = list(Room.objects.select_for_update().filter(pk__in=room_ids).order_by("pk"))
    if len(rooms) != len(room_ids):
        raise ValidationError("One or more rooms do not exist.")
    if available_rooms(booking).filter(pk__in=room_ids).count() != len(room_ids):
        raise ValidationError("One or more rooms are unavailable or have the wrong type.")
    if booking.allotments.exists():
        raise ValidationError("Rooms have already been allotted.")
    RoomAllotment.objects.bulk_create([RoomAllotment(booking=booking, room=r) for r in rooms])
    booking.status = "confirmed"
    booking.save()


def money(value):
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def cancellation_charge(booking, when):
    days = (booking.check_in_date - timezone.localtime(when).date()).days
    fraction = Decimal("0") if days >= 7 else Decimal("0.25") if days > 0 else Decimal("0.5")
    if not fraction:
        return Decimal("0.00")
    return money(tariff_for(booking) * booking.number_of_rooms * fraction)


def create_bill(booking, *, cancellation=None):
    if Bill.objects.filter(booking=booking).exists():
        raise ValidationError("A bill already exists; generated billing records are immutable.")
    room = Decimal("0.00")
    meal = Decimal("0.00")
    if cancellation is None:
        room = money(
            tariff_for(booking)
            * max(1, (booking.check_out_date - booking.check_in_date).days)
            * booking.number_of_rooms
        )
        meal = money(sum((m.rate * m.quantity for m in booking.meal_bookings.all()), Decimal(0)))
    cancellation = cancellation or Decimal("0.00")
    if room + meal + cancellation > Decimal("99999999.99"):
        raise ValidationError("Bill amount exceeds the supported monetary limit.")
    return Bill.objects.create(
        booking=booking,
        room_charge=room,
        meal_charge=meal,
        cancellation_charge=cancellation,
        total_amount=room + meal + cancellation,
        is_immutable=True,
    )


def queue_notification(event, *, key, booking=None, role="", recipient_id=None, **payload):
    from .models import Notification

    return Notification.objects.get_or_create(
        key=key,
        defaults={
            "event": event,
            "booking": booking,
            "recipient_role": role,
            "recipient_id": recipient_id,
            "payload": payload,
        },
    )[0]


def inventory_alert(item):
    if item.is_below_threshold():
        queue_notification(
            "inventory_threshold",
            key=f"inventory:{item.pk}:{item.updated_at.isoformat()}",
            role="vh_caretaker",
            item_id=item.pk,
            quantity=item.quantity,
        )
