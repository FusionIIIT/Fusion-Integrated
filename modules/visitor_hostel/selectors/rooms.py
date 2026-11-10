"""Room availability (AFR-VH-015, BR-VH-004). One query, the same for online
and offline bookings."""
from __future__ import annotations

from datetime import date, timedelta

from django.db.models import Q, QuerySet

from modules.visitor_hostel.domain import state_machine as sm
from modules.visitor_hostel.models import Room, RoomAllotment

#: Bookings whose allotment still holds its rooms.
HOLDING = (sm.ROOM_ALLOTTED, sm.CHECKED_IN)


def _end(arrival: date, departure: date) -> date:
    """A same-day stay still occupies the room for that day."""
    return max(departure, arrival + timedelta(days=1))


def occupied_room_ids(arrival: date, departure: date,
                      exclude_booking_id: int | None = None) -> set[int]:
    end = _end(arrival, departure)
    qs = RoomAllotment.objects.filter(
        booking__status__in=HOLDING,
        booking__arrival_date__lt=end,
    ).filter(Q(booking__departure_date__gt=arrival)
             | Q(booking__departure_date=arrival,
                 booking__arrival_date=arrival))
    if exclude_booking_id is not None:
        qs = qs.exclude(booking_id=exclude_booking_id)
    return set(qs.values_list("room_id", flat=True))


def available_rooms(arrival: date, departure: date,
                    exclude_booking_id: int | None = None) -> QuerySet[Room]:
    taken = occupied_room_ids(arrival, departure, exclude_booking_id)
    return Room.objects.filter(is_active=True).exclude(pk__in=taken).order_by("number")
