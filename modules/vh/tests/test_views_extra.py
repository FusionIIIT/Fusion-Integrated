# Unit tests for remaining DRF view endpoints in modules/vh/api/views.py
from datetime import date, timedelta

import pytest

from modules.vh.models.booking import Booking

pytestmark = pytest.mark.django_db


def test_room_views_crud(caretaker_client):
    today = date.today()
    resp = caretaker_client.get(
        f"/api/v1/vh/rooms/availability/?arrival_date={today}&departure_date={today + timedelta(days=2)}"
    )
    assert resp.status_code == 200


def test_tariff_views(incharge_client):
    eff = str(date.today())
    resp = incharge_client.post(
        "/api/v1/vh/tariffs/",
        {
            "category": "C",
            "room_type": "non_suite",
            "occupancy": "single",
            "daily_rate": "400.00",
            "effective_from": eff,
        },
        format="json",
    )
    assert resp.status_code == 201

    resp_list = incharge_client.get("/api/v1/vh/tariffs/?category=C")
    assert resp_list.status_code == 200


def test_inventory_views_crud(caretaker_client):
    resp = caretaker_client.post(
        "/api/v1/vh/inventory/",
        {
            "item_name": "Blanket Woolen",
            "category": "linen",
            "current_quantity": 25,
            "minimum_threshold": 10,
            "unit": "pieces",
        },
        format="json",
    )
    assert resp.status_code == 200

    resp_list = caretaker_client.get("/api/v1/vh/inventory/?category=linen")
    assert resp_list.status_code == 200


def test_booking_modify_view(indenter_client):
    b = Booking.objects.create(
        booking_reference="VH-MOD-VIEW-1",
        indenter_id=101,
        arrival_date=date.today() + timedelta(days=10),
        departure_date=date.today() + timedelta(days=12),
        status="pending",
    )
    resp = indenter_client.post(
        f"/api/v1/vh/bookings/{b.id}/modify/",
        {"visit_purpose": "Altered guest lecture purpose"},
        format="json",
    )
    assert resp.status_code == 200
    assert resp.data["visit_purpose"] == "Altered guest lecture purpose"


def test_bill_generate_and_detail_views(caretaker_client):
    b = Booking.objects.create(
        booking_reference="VH-BILL-VIEW-2",
        indenter_id=101,
        visitor_category="A",
        arrival_date=date.today(),
        departure_date=date.today() + timedelta(days=2),
        status="approved",
    )
    resp = caretaker_client.post(f"/api/v1/vh/bookings/{b.id}/bill/", format="json")
    assert resp.status_code == 201
    assert "total_amount" in resp.data
