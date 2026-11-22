# Adversarial security and state integrity tests for vh module.
from datetime import date, timedelta
from decimal import Decimal

import pytest

from modules.vh.models.booking import Booking
from modules.vh.models.tariff import TariffConfig
from modules.vh.services.billing import generate_bill

pytestmark = pytest.mark.django_db


def test_cannot_modify_cancelled_or_rejected_booking(indenter_client):
    # Step 5.11: Terminal or cancelled booking cannot be modified
    booking = Booking.objects.create(
        booking_reference="VH-ADV-1",
        indenter_id=101,
        arrival_date=date.today() + timedelta(days=5),
        departure_date=date.today() + timedelta(days=7),
        status="cancelled",
    )
    resp = indenter_client.post(
        f"/api/v1/vh/bookings/{booking.id}/modify/",
        {"visit_purpose": "Trying to modify cancelled booking"},
    )
    assert resp.status_code == 409
    assert resp.data["error"]["code"] == "conflict"


def test_cannot_cancel_checked_in_stay(indenter_client):
    # Once guest checks in, pre-arrival cancellation is illegal
    booking = Booking.objects.create(
        booking_reference="VH-ADV-2",
        indenter_id=101,
        arrival_date=date.today() - timedelta(days=1),
        departure_date=date.today() + timedelta(days=2),
        status="checked_in",
    )
    resp = indenter_client.post(
        f"/api/v1/vh/bookings/{booking.id}/cancel/",
        {"reason": "Guest already checked in"},
    )
    assert resp.status_code == 409
    assert resp.data["error"]["code"] == "conflict"


def test_cannot_allot_rooms_to_pending_booking(caretaker_client, sample_rooms):
    # BR-VH-012: Room allotment strictly forbidden before booking approval
    r1, _, _ = sample_rooms
    booking = Booking.objects.create(
        booking_reference="VH-ADV-3",
        indenter_id=101,
        arrival_date=date.today() + timedelta(days=2),
        departure_date=date.today() + timedelta(days=4),
        status="pending",
    )
    resp = caretaker_client.post(
        f"/api/v1/vh/bookings/{booking.id}/allot-rooms/",
        {"room_ids": [r1.id], "occupancy_type": "single"},
    )
    assert resp.status_code == 409
    assert resp.data["error"]["code"] == "conflict"


def test_cannot_reduce_inventory_below_zero(caretaker_client, sample_inventory):
    # Negative stock balance is strictly refused
    item1, _ = sample_inventory  # current_quantity = 20
    resp = caretaker_client.post(
        "/api/v1/vh/inventory/",
        {"id": item1.id, "item_name": item1.item_name, "current_quantity": -5},
    )
    assert resp.status_code == 400


def test_cannot_order_meals_outside_stay_duration(caretaker_client):
    # BR-VH-031: Meal order on date outside stay duration is refused
    booking = Booking.objects.create(
        booking_reference="VH-ADV-MEAL",
        indenter_id=101,
        arrival_date=date(2026, 12, 10),
        departure_date=date(2026, 12, 12),
        status="room_allotted",
    )
    resp = caretaker_client.post(
        f"/api/v1/vh/bookings/{booking.id}/meals/",
        {
            "meal_date": "2026-12-15",
            "meal_option": "full_day",
            "quantity": 1,
        },
    )
    assert resp.status_code == 422


def test_tariff_change_does_not_mutate_historical_settled_bill(
    caretaker_client, sample_tariffs, sample_rooms
):
    # BR-VH-024, BR-VH-037: Settled bill is immutable against later tariff changes
    booking = Booking.objects.create(
        booking_reference="VH-HIST-1",
        indenter_id=101,
        visitor_category="A",
        arrival_date=date(2026, 10, 1),
        departure_date=date(2026, 10, 3),
        status="checked_out",
    )
    bill = generate_bill(booking.id, None)
    initial_total = bill.total_amount

    # Settle bill
    caretaker_client.post(
        f"/api/v1/vh/bills/{bill.id}/settle/",
        {"amount_paid": str(initial_total), "receipt_number": "RCP-HIST-1"},
    )
    bill.refresh_from_db()
    assert bill.status == "settled"
    assert bill.is_immutable is True

    # Mutate/increase tariffs in system
    TariffConfig.objects.filter(category="A").update(daily_rate=Decimal("9999.00"))

    # Regenerate attempt
    regenerated = generate_bill(booking.id, None)
    assert regenerated.total_amount == initial_total
    assert regenerated.total_amount != Decimal("9999.00")
