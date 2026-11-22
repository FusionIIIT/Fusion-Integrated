# Unit tests for query selectors in modules/vh/selectors/
from datetime import date, timedelta
from decimal import Decimal

import pytest

from conftest import make_principal
from core.api.exceptions import NotFoundError
from modules.vh.models.bill import Bill
from modules.vh.models.booking import Booking
from modules.vh.models.inventory import InventoryItem, InventoryReplenishment
from modules.vh.models.meal import MealBooking
from modules.vh.models.room import Room, RoomAllotment
from modules.vh.models.tariff import TariffConfig
from modules.vh.selectors import billing as billing_sel
from modules.vh.selectors import bookings as booking_sel
from modules.vh.selectors import inventory as inventory_sel
from modules.vh.selectors import meals as meal_sel
from modules.vh.selectors import reports as reports_sel
from modules.vh.selectors import rooms as room_sel
from modules.vh.selectors import tariffs as tariff_sel

pytestmark = pytest.mark.django_db


def test_billing_selectors():
    principal = make_principal(user_id=201, permissions=("vh.bill.view", "vh.booking.review"))
    b = Booking.objects.create(
        booking_reference="VH-SEL-BILL-1",
        indenter_id=101,
        arrival_date=date.today(),
        departure_date=date.today() + timedelta(days=2),
        status="checked_out",
    )
    bill = Bill.objects.create(
        booking=b,
        bill_number="BILL-2026-SEL-01",
        total_amount=Decimal("1200.00"),
        status="generated",
    )
    assert billing_sel.get_bill_for_booking(b.id, principal) == bill

    b_nobill = Booking.objects.create(
        booking_reference="VH-SEL-NOBILL",
        indenter_id=201,
        arrival_date=date.today(),
        departure_date=date.today() + timedelta(days=2),
        status="pending",
    )
    with pytest.raises(NotFoundError):
        billing_sel.get_bill_for_booking(b_nobill.id, principal)


def test_booking_sub_selectors():
    caretaker = make_principal(user_id=201, permissions=("vh.booking.review",))
    b1 = Booking.objects.create(
        booking_reference="VH-SEL-BK-1",
        indenter_id=101,
        arrival_date=date.today() + timedelta(days=5),
        departure_date=date.today() + timedelta(days=7),
        status="pending",
    )
    b2 = Booking.objects.create(
        booking_reference="VH-SEL-BK-2",
        indenter_id=101,
        arrival_date=date.today() + timedelta(days=8),
        departure_date=date.today() + timedelta(days=10),
        status="forwarded",
    )
    b3 = Booking.objects.create(
        booking_reference="VH-SEL-BK-3",
        indenter_id=101,
        arrival_date=date.today() + timedelta(days=12),
        departure_date=date.today() + timedelta(days=14),
        status="cancellation_requested",
    )

    pending = booking_sel.list_pending_bookings(caretaker)
    assert b1 in pending
    assert b2 not in pending
    assert booking_sel.get_booking_detail(b1.id, caretaker) == b1

    forwarded = booking_sel.list_forwarded_bookings(caretaker)
    assert b2 in forwarded
    assert b1 not in forwarded

    cancels = booking_sel.list_cancellation_requests(caretaker)
    assert b3 in cancels


def test_inventory_selectors():
    item = InventoryItem.objects.create(
        item_name="Pillow", category="linen", current_quantity=15, minimum_threshold=10
    )
    rep = InventoryReplenishment.objects.create(
        item=item, requested_quantity=20, status="pending", requested_by=201
    )

    items = inventory_sel.list_inventory_items(category="linen")
    assert item in items

    reps = inventory_sel.list_replenishment_requests(status="pending")
    assert rep in reps


def test_meal_selectors():
    principal = make_principal(user_id=201, permissions=("vh.meal.view", "vh.booking.review"))
    b = Booking.objects.create(
        booking_reference="VH-SEL-MEAL",
        indenter_id=101,
        arrival_date=date.today(),
        departure_date=date.today() + timedelta(days=2),
        status="checked_in",
    )
    meal = MealBooking.objects.create(
        booking=b,
        meal_date=date.today(),
        meal_option="full_day",
        quantity=2,
        rate=Decimal("150.00"),
        amount=Decimal("300.00"),
    )
    meals = meal_sel.list_booking_meals(b.id, principal)
    assert meal in meals


def test_room_selectors():
    r1 = Room.objects.create(room_number="R201", room_type="suite", capacity=2, is_active=True)
    r2 = Room.objects.create(room_number="R202", room_type="non_suite", capacity=2, is_active=False)

    active_rooms = room_sel.list_rooms(room_type="suite", is_active=True)
    assert r1 in active_rooms
    assert r2 not in active_rooms

    today = date.today()
    avail = room_sel.check_room_availability(today, today + timedelta(days=2))
    assert r1 in avail

    avail_suites = room_sel.check_room_availability(
        today, today + timedelta(days=2), room_type="suite"
    )
    assert r1 in avail_suites


def test_tariff_selectors():
    eff = date.today() - timedelta(days=10)
    t = TariffConfig.objects.create(
        category="A",
        room_type="suite",
        occupancy="single",
        daily_rate=Decimal("1000.00"),
        effective_from=eff,
    )
    active_tariffs = tariff_sel.list_tariffs(active_only=True)
    assert t in active_tariffs

    rate = tariff_sel.get_applicable_tariff("A", "suite", "single", date.today())
    assert rate == Decimal("1000.00")


def test_reports_selectors():
    b = Booking.objects.create(
        booking_reference="VH-REP-BK",
        indenter_id=101,
        visitor_category="A",
        arrival_date=date.today(),
        departure_date=date.today() + timedelta(days=2),
        status="checked_in",
    )
    r = Room.objects.create(room_number="R301", room_type="suite", capacity=2, is_active=True)
    RoomAllotment.objects.create(booking=b, room=r, occupancy_type="single", allotted_by=201)

    occ = reports_sel.get_daily_occupancy_report(date.today())
    assert occ["total_rooms_occupied"] >= 1

    summary = reports_sel.get_booking_summary_report()
    assert summary["total_bookings"] >= 1

    billing = reports_sel.get_revenue_summary_report()
    assert "total_billed" in billing

    arrivals = reports_sel.get_arrivals_departures_report(date.today())
    assert "arrivals_count" in arrivals

    pending = reports_sel.get_pending_approvals_report()
    assert "pending_caretaker_review" in pending

    exceptions = reports_sel.get_stay_exception_logs()
    assert isinstance(exceptions, list)

    cat_occ = reports_sel.get_category_occupancy_report()
    assert isinstance(cat_occ, list)

    inv = reports_sel.get_inventory_usage_report()
    assert isinstance(inv, list)
