# Extended specification matrix verification tests for VHMS.
# Verifies cross-cutting constraints between CFRs, Business Rules, and Workflows.
from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from modules.vh.models.alerts import StayAlert
from modules.vh.models.booking import Booking
from modules.vh.models.inventory import InventoryItem, InventoryReplenishment
from modules.vh.models.room import RoomAllotment
from modules.vh.services.alerts import evaluate_no_shows, evaluate_overstays

pytestmark = pytest.mark.django_db


def test_spec_matrix_001_modification_refused_after_checkin(indenter_client, sample_rooms):
    """
    CFR-VH-005 & BR-VH-010: Pre-arrival modification request is refused once guest has checked in.
    """
    r1, _, _ = sample_rooms
    today = date.today()
    b = Booking.objects.create(
        booking_reference="BK-SPEC-MOD-01",
        indenter_id=101,
        arrival_date=today,
        departure_date=today + timedelta(days=3),
        status="checked_in",
        checkin_time=timezone.now(),
    )
    RoomAllotment.objects.create(booking=b, room=r1, allotted_by=201, occupancy_type="single")

    payload = {"departure_date": str(today + timedelta(days=5))}
    resp = indenter_client.post(f"/api/v1/vh/bookings/{b.id}/modify/", payload, format="json")
    assert resp.status_code in [400, 409, 422]


def test_spec_matrix_002_zero_cancellation_bill(caretaker_client, sample_tariffs):
    """
    CFR-VH-006, BR-VH-007, BR-VH-035: Cancellation with 7+ days notice produces a 0.00 bill.
    """
    b = Booking.objects.create(
        booking_reference="BK-SPEC-CANC-0",
        indenter_id=101,
        visitor_category="A",
        visit_purpose="Zero cancel test",
        arrival_date=date.today() + timedelta(days=10),
        departure_date=date.today() + timedelta(days=12),
        status="cancelled",
        cancellation_charge_percentage=Decimal("0.00"),
    )
    resp = caretaker_client.post(f"/api/v1/vh/bookings/{b.id}/bill/", format="json")
    assert resp.status_code == 201
    assert Decimal(str(resp.data["cancellation_charge_total"])) == Decimal("0.00")
    assert Decimal(str(resp.data["total_amount"])) == Decimal("0.00")


def test_spec_matrix_003_replenishment_approval_updates_stock(incharge_client):
    """
    CFR-VH-013, UC-VH-015: In-Charge approval of replenishment increments current inventory stock.
    """
    item = InventoryItem.objects.create(
        item_name="Pillow Cases Special",
        category="linen",
        current_quantity=4,
        minimum_threshold=10,
        unit="pieces",
        is_threshold_alert=True,
    )
    rep = InventoryReplenishment.objects.create(
        item=item,
        requested_quantity=15,
        status="pending",
        requested_by=201,
        remarks="Urgent restock",
    )
    resp = incharge_client.post(
        f"/api/v1/vh/inventory/replenishments/{rep.id}/approve/",
        {"decision": "approved", "remarks": "Approved by In-Charge"},
        format="json",
    )
    assert resp.status_code == 200
    item.refresh_from_db()
    assert item.current_quantity == 19
    assert item.is_threshold_alert is False


def test_spec_matrix_004_caretaker_operational_report(caretaker_client, sample_rooms):
    """
    CFR-VH-015, UC-VH-018: Caretaker operational reports aggregate occupancy and room counts.
    """
    resp = caretaker_client.get("/api/v1/vh/reports/caretaker/")
    assert resp.status_code == 200
    assert "total_rooms_occupied" in resp.data
    assert "total_occupants" in resp.data
    assert "rooms" in resp.data


def test_spec_matrix_005_supervisor_executive_report(incharge_client):
    """
    CFR-VH-016, UC-VH-017: VH In-Charge executive reports aggregate booking statistics and revenue.
    """
    resp = incharge_client.get("/api/v1/vh/reports/incharge/")
    assert resp.status_code == 200
    assert "total_bookings" in resp.data
    assert "offline_bookings" in resp.data
    assert "status_distribution" in resp.data


def test_spec_matrix_006_stay_exception_lifecycle(sample_rooms):
    """
    CFR-VH-008, BR-VH-017, BR-VH-018: Stay exception alerts for no-show and overstay.
    """
    r1, _, _ = sample_rooms
    today = date.today()

    # 1. No-show alert creation
    b1 = Booking.objects.create(
        booking_reference="BK-SPEC-NS",
        indenter_id=101,
        arrival_date=today - timedelta(days=1),
        departure_date=today + timedelta(days=2),
        status="room_allotted",
    )
    RoomAllotment.objects.create(booking=b1, room=r1, allotted_by=201)
    ns_count = evaluate_no_shows()
    assert ns_count >= 1
    assert StayAlert.objects.filter(booking=b1, alert_type="no_show").exists()

    # 2. Overstay alert creation
    b2 = Booking.objects.create(
        booking_reference="BK-SPEC-OS",
        indenter_id=101,
        arrival_date=today - timedelta(days=4),
        departure_date=today - timedelta(days=1),
        status="checked_in",
        checkin_time=timezone.now() - timedelta(days=4),
    )
    os_count = evaluate_overstays()
    assert os_count >= 1
    assert StayAlert.objects.filter(booking=b2, alert_type="overstay").exists()
