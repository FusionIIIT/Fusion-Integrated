# Query budget tests: Asserts constant queries preventing N+1 leaks.
from datetime import date

import pytest

from modules.vh.models.booking import Booking
from modules.vh.models.room import Room, RoomAllotment
from modules.vh.models.visitor import VisitorDetail

pytestmark = pytest.mark.django_db


def _populate_bookings(count: int, room: Room, offset: int = 0):
    for i in range(count):
        b = Booking.objects.create(
            booking_reference=f"VH-BUDGET-{offset + i}",
            indenter_id=101,
            arrival_date=date(2026, 12, 1),
            departure_date=date(2026, 12, 5),
            status="room_allotted",
        )
        VisitorDetail.objects.create(booking=b, name=f"Guest {offset + i}")
        RoomAllotment.objects.create(booking=b, room=room, occupancy_type="single", allotted_by=201)


def test_booking_list_query_budget_independent_of_row_count(
    caretaker_client, django_assert_num_queries
):
    # Step 5.8: Query count must be strictly constant between 2 and 15 rows
    room = Room.objects.create(room_number="999", room_type="suite", capacity=2, is_active=True)

    # 1. Measure query count with 2 bookings
    _populate_bookings(2, room, offset=0)
    with django_assert_num_queries(3):
        resp = caretaker_client.get("/api/v1/vh/bookings/")
        assert resp.status_code == 200
        assert len(resp.data) == 2

    # 2. Add 10 more bookings; query count must stay identical (3 queries: bookings, visitors, allotments)
    _populate_bookings(10, room, offset=2)
    with django_assert_num_queries(3):
        resp = caretaker_client.get("/api/v1/vh/bookings/")
        assert resp.status_code == 200
        assert len(resp.data) == 12
