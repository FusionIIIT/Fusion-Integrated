# Concurrency tests: Real threads against database with barrier synchronization.
import threading
from datetime import date
from decimal import Decimal

import pytest
from django import db

from conftest import make_principal
from core.api.exceptions import ConflictError
from modules.vh.models.bill import Bill
from modules.vh.models.booking import Booking
from modules.vh.models.room import Room, RoomAllotment
from modules.vh.services.billing import record_offline_settlement
from modules.vh.services.stays import allot_rooms

pytestmark = pytest.mark.django_db(transaction=True)


def test_concurrent_room_allotment_refuses_double_booking():
    # Step 5.7: Simultaneous allotment of the same room to two bookings: exactly one succeeds
    room = Room.objects.create(room_number="301", room_type="suite", capacity=2, is_active=True)
    b1 = Booking.objects.create(
        booking_reference="VH-CONC-1",
        indenter_id=1,
        arrival_date=date(2026, 12, 1),
        departure_date=date(2026, 12, 5),
        status="approved",
    )
    b2 = Booking.objects.create(
        booking_reference="VH-CONC-2",
        indenter_id=2,
        arrival_date=date(2026, 12, 1),
        departure_date=date(2026, 12, 5),
        status="approved",
    )

    barrier = threading.Barrier(2)
    results = []
    errors = []

    def _attempt(b_id):
        principal = make_principal(user_id=201, permissions=("vh.room.assign",))
        try:
            barrier.wait(timeout=5)
            allotment = allot_rooms(b_id, [room.id], "single", principal)
            results.append((b_id, allotment))
        except Exception as err:  # noqa: BLE001
            errors.append((b_id, err))
        finally:
            db.connections.close_all()

    t1 = threading.Thread(target=_attempt, args=(b1.id,))
    t2 = threading.Thread(target=_attempt, args=(b2.id,))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    # Exactly one thread succeeds in allotting the room
    assert len(results) == 1
    assert len(errors) == 1
    assert isinstance(errors[0][1], ConflictError)
    assert RoomAllotment.objects.filter(room=room).count() == 1


def test_concurrent_bill_settlement_refuses_double_settlement():
    # Simultaneous settlement calls on the same bill: exactly one succeeds
    booking = Booking.objects.create(
        booking_reference="VH-BILL-CONC",
        indenter_id=1,
        arrival_date=date(2026, 12, 1),
        departure_date=date(2026, 12, 3),
        status="checked_out",
    )
    bill = Bill.objects.create(
        booking=booking,
        bill_number="BILL-CONC-1",
        visitor_category="A",
        room_rent_total=Decimal("1000.00"),
        total_amount=Decimal("1000.00"),
        billing_responsibility="visitor",
        status="generated",
    )

    barrier = threading.Barrier(2)
    results = []
    errors = []

    def _attempt():
        principal = make_principal(user_id=201, permissions=("vh.bill.manage",))
        try:
            barrier.wait(timeout=5)
            settlement = record_offline_settlement(
                bill.id, Decimal("1000.00"), "RCP-1", "Cash", principal
            )
            results.append(settlement)
        except Exception as err:  # noqa: BLE001
            errors.append(err)
        finally:
            db.connections.close_all()

    t1 = threading.Thread(target=_attempt)
    t2 = threading.Thread(target=_attempt)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert len(results) == 1
    assert len(errors) == 1
    assert isinstance(errors[0], ConflictError)
    bill.refresh_from_db()
    assert bill.status == "settled"
