"""Read selectors for hostels and rooms.
"""
from django.db.models import QuerySet

from modules.hostel.models import Hostel, RoomAllotment


def get_all_hostels() -> QuerySet[Hostel]:
    return Hostel.objects.all().order_by("name")


def get_active_allotments_for_user(user_id: int) -> QuerySet[RoomAllotment]:
    return RoomAllotment.objects.filter(
        user_id=user_id, is_active=True
    ).select_related("room", "room__hostel")
