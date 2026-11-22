# Room queries and availability checking for VHMS.
from datetime import date

from django.db.models import QuerySet

from modules.vh.models.room import Room, RoomAllotment


def list_rooms(room_type: str | None = None, is_active: bool = True) -> QuerySet[Room]:
    # Returns hostel rooms filtered by type and active status.
    qs = Room.objects.filter(is_active=is_active).order_by("room_number")
    if room_type:
        qs = qs.filter(room_type=room_type.lower())
    return qs


def check_room_availability(
    arrival_date: date,
    departure_date: date,
    room_type: str | None = None,
) -> QuerySet[Room]:
    # AFR-VH-015, AFR-VH-024: Checks available rooms not overlapping with active stays.
    active_occupancies = RoomAllotment.objects.filter(
        booking__status__in=["approved", "approved_offline", "room_allotted", "checked_in"],
        booking__arrival_date__lte=departure_date,
        booking__departure_date__gte=arrival_date,
    ).values_list("room_id", flat=True)

    available = Room.objects.filter(is_active=True).exclude(id__in=active_occupancies)
    if room_type:
        available = available.filter(room_type=room_type.lower())
    return available.order_by("room_number")
