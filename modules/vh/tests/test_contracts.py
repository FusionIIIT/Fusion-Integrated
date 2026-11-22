# Contract unit tests for modules/vh/contracts.py
from datetime import date
from decimal import Decimal

import pytest

from modules.vh.contracts import get_active_stays, get_billing_summaries
from modules.vh.models.bill import Bill
from modules.vh.models.booking import Booking
from modules.vh.models.room import Room, RoomAllotment
from modules.vh.models.visitor import VisitorDetail

pytestmark = pytest.mark.django_db


def test_get_active_stays_contract():
    assert get_active_stays([]) == {}
    assert get_active_stays([None]) == {}

    room = Room.objects.create(room_number="101", room_type="suite", capacity=2)
    b1 = Booking.objects.create(
        booking_reference="VH-CTR-01",
        indenter_id=101,
        arrival_date=date(2026, 12, 1),
        departure_date=date(2026, 12, 5),
        status="room_allotted",
    )
    VisitorDetail.objects.create(booking=b1, name="Prof. Turing")
    RoomAllotment.objects.create(booking=b1, room=room, occupancy_type="single", allotted_by=201)

    stays = get_active_stays([b1.id, 999999])
    assert len(stays) == 1
    dto = stays[b1.id]
    assert dto.booking_id == b1.id
    assert dto.booking_reference == "VH-CTR-01"
    assert dto.visitor_name == "Prof. Turing"
    assert dto.room_numbers == ["101"]
    assert dto.status == "room_allotted"


def test_get_billing_summaries_contract():
    assert get_billing_summaries([]) == {}
    assert get_billing_summaries([None]) == {}

    b1 = Booking.objects.create(
        booking_reference="VH-CTR-02",
        indenter_id=101,
        arrival_date=date(2026, 12, 1),
        departure_date=date(2026, 12, 5),
        status="checked_out",
    )
    Bill.objects.create(
        booking=b1,
        bill_number="BILL-2026-CTR01",
        total_amount=Decimal("1500.00"),
        billing_responsibility="institute",
        status="settled",
    )

    summaries = get_billing_summaries([b1.id, 888888])
    assert len(summaries) == 1
    summary = summaries[b1.id]
    assert summary.booking_id == b1.id
    assert summary.bill_number == "BILL-2026-CTR01"
    assert summary.total_amount == 1500.0
    assert summary.billing_responsibility == "institute"
    assert summary.is_settled is True
