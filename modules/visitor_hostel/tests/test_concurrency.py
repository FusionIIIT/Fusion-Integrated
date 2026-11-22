"""Real row-lock regression: run with --ds=config.settings.test_postgres --migrations."""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

import pytest
from django.db import close_old_connections, connection, transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from modules.visitor_hostel.models import BookingRequest, Room, RoomAllotment
from modules.visitor_hostel.services import allot


@pytest.mark.django_db(transaction=True)
def test_two_bookings_cannot_concurrently_reserve_one_room():
    if connection.vendor != "postgresql":
        pytest.skip("Requires PostgreSQL row locks; covered by the PostgreSQL CI job.")
    room = Room.objects.create(room_number="RACE", room_type="suite")
    bookings = [
        BookingRequest.objects.create(
            indenter_id=i,
            visitor_name=f"Guest {i}",
            visitor_category="A",
            purpose="Visit",
            status="approved",
            room_type="suite",
            check_in_date=timezone.localdate() + timedelta(days=2),
            check_out_date=timezone.localdate() + timedelta(days=4),
        )
        for i in (1, 2)
    ]
    barrier = Barrier(2)

    def reserve(pk):
        close_old_connections()
        try:
            with transaction.atomic():
                booking = BookingRequest.objects.select_for_update().get(pk=pk)
                barrier.wait(timeout=10)
                allot(booking, [room.pk])
        except ValidationError:
            return "unavailable"
        else:
            return "reserved"
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(reserve, [booking.pk for booking in bookings]))
    assert sorted(outcomes) == ["reserved", "unavailable"]
    assert RoomAllotment.objects.filter(room=room).count() == 1
