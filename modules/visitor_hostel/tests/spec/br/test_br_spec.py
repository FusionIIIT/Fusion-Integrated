"""Business-rule boundaries verified against persisted records."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from freezegun import freeze_time

from modules.visitor_hostel.models import Bill, InventoryItem, RoomAllotment, VisitorCategoryTariff
from modules.visitor_hostel.services import cancellation_charge, tariff_for
from modules.visitor_hostel.tests.spec.conftest import endpoint

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("days,expected", [(8, "0"), (7, "0"), (6, "100"), (1, "100"), (0, "200")])
def test_cancellation_boundaries(booking, tariff, days, expected):
    """
    Test ID: BR-011-band1
    Source ID: BR-VH-011
    Purpose: Verify tiered cancellation charge calculation based on notification lead time.
    Preconditions: Booking with active tariff of 400.00.
    Action: Calculate cancellation charge for lead times (8, 7, 6, 1, 0 days).
    Expected: >=7 days: 0; 1-6 days: 100 (25%); same-day (0): 200 (50%).
    """
    with freeze_time("2026-11-22 10:00:00"):
        booking.check_in_date = timezone.localdate() + timedelta(days=days)
        assert cancellation_charge(booking, timezone.now()) == Decimal(expected)


def test_cancellation_accounts_for_all_rooms(booking, tariff):
    """
    Test ID: BR-011-band2
    Source ID: BR-VH-011
    Purpose: Verify cancellation charge multiplies accurately across multiple requested rooms.
    Preconditions: Booking with 3 rooms, same-day cancellation.
    Action: Calculate cancellation charge for 3 rooms at 50% rate.
    Expected: 3 rooms * 200.00 = 600.00.
    """
    booking.number_of_rooms = 3
    booking.check_in_date = timezone.localdate()
    assert cancellation_charge(booking, timezone.now()) == Decimal("600.00")


def test_tariff_effective_on_arrival_not_future(booking, tariff):
    """
    Test ID: BR-023
    Source ID: BR-VH-023
    Purpose: Verify tariff lookup uses effective rate on arrival date, ignoring future-dated changes.
    Preconditions: Base tariff 400 effective 2020; future tariff 900 effective day after check-in.
    Action: Query applicable tariff for booking.
    Expected: Base rate 400 applies.
    """
    VisitorCategoryTariff.objects.create(
        category="A",
        room_type="suite",
        occupancy="single",
        daily_rate=Decimal("900"),
        effective_from=booking.check_in_date + timedelta(days=1),
    )
    assert tariff_for(booking) == Decimal("400")


@pytest.mark.parametrize("quantity,expected", [(4, True), (5, False), (6, False)])
def test_inventory_threshold_is_strict(quantity, expected):
    """
    Test ID: BR-041-below
    Source ID: BR-VH-041
    Purpose: Verify inventory low-stock alert triggers strictly below minimum threshold (strictly <).
    Preconditions: Item with minimum_threshold = 5.
    Action: Evaluate is_below_threshold for quantity 4, 5, and 6.
    Expected: True for 4 (<5); False for 5 (=5) and 6 (>5).
    """
    assert InventoryItem(quantity=quantity, minimum_threshold=5).is_below_threshold() is expected


def test_checkout_without_tariff_is_atomic(actor, booking, room):
    """
    Test ID: BR-031-outside
    Source ID: BR-VH-031
    Purpose: Verify checkout transaction rolls back atomically if tariff lookup fails.
    Preconditions: Checked-in guest without defined tariff.
    Action: POST /api/v1/visitor-hostel/bookings/{id}/check-out/.
    Expected: HTTP 400 Bad Request; booking remains checked-in, room occupied, no bill created.
    """
    booking.status = "checked_in"
    booking.save()
    room.status = "occupied"
    room.save()
    allotment = RoomAllotment.objects.create(
        booking=booking, room=room, actual_check_in=timezone.now()
    )
    response = actor("vh_caretaker").post(endpoint(booking, "check-out"))
    assert response.status_code == 400
    booking.refresh_from_db()
    room.refresh_from_db()
    allotment.refresh_from_db()
    assert booking.status == "checked_in"
    assert room.status == "occupied"
    assert allotment.actual_check_out is None
    assert not Bill.objects.exists()


def test_bill_survives_tariff_change_and_checkout_retry(actor, booking, tariff):
    """
    Test ID: BR-035
    Source ID: BR-VH-035
    Purpose: Verify generated bill is immutable against subsequent tariff edits or checkout retries.
    Preconditions: Checked-in booking with tariff 400.
    Action: Checkout, modify tariff to 999, repeat checkout request.
    Expected: Bill amount unchanged (800.00), only 1 bill exists, is_immutable True.
    """
    booking.status = "checked_in"
    booking.save()
    client = actor("vh_caretaker")
    first = client.post(endpoint(booking, "check-out"))
    assert first.status_code == 200
    tariff.daily_rate = 999
    tariff.save()
    second = client.post(endpoint(booking, "check-out"))
    assert second.data["total_amount"] == first.data["total_amount"] == "800.00"
    assert Bill.objects.count() == 1
    assert Bill.objects.get().is_immutable


@pytest.mark.parametrize("status", ["pending", "approved", "checked_out", "cancelled"])
def test_meals_only_for_current_residents(actor, booking, status):
    """
    Test ID: BR-024
    Source ID: BR-VH-024
    Purpose: Verify meal booking is allowed strictly for residents with active checked_in status.
    Preconditions: Booking in non-checked-in states.
    Action: POST /api/v1/visitor-hostel/bookings/{id}/meals/.
    Expected: HTTP 400 Bad Request.
    """
    booking.status = status
    booking.save()
    response = actor("vh_caretaker").post(
        endpoint(booking, "meals"),
        {"date": str(booking.check_in_date), "meal_type": "lunch", "quantity": 1, "rate": "60"},
        format="json",
    )
    assert response.status_code == 400


def test_meal_dates_and_negative_amounts_rejected(actor, booking):
    """
    Test ID: BR-025-denied
    Source ID: BR-VH-025
    Purpose: Verify meal booking validates stay date range and non-negative rates.
    Preconditions: Checked-in booking.
    Action: POST meal booking with date prior to check-in or negative rate.
    Expected: HTTP 400 Bad Request; no meal record created.
    """
    booking.status = "checked_in"
    booking.save()
    client = actor("vh_caretaker")
    data = {
        "date": str(booking.check_in_date - timedelta(days=1)),
        "meal_type": "lunch",
        "quantity": 1,
        "rate": "60",
    }
    assert client.post(endpoint(booking, "meals"), data, format="json").status_code == 400
    data.update(date=str(booking.check_in_date), rate="-1")
    assert client.post(endpoint(booking, "meals"), data, format="json").status_code == 400
    assert not booking.meal_bookings.exists()

