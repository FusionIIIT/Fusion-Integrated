"""Unit and API tests for the Visitors Hostel (VH) module."""
from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from modules.vh import contracts
from modules.vh.models import (
    Booking,
    BookingStatus,
    InventoryItem,
    Room,
    RoomStatus,
    Tariff,
    VisitorCategory,
)


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def visitor_category(db):
    return VisitorCategory.objects.create(
        code=VisitorCategory.CATEGORY_A,
        name="Institute Guests / Official",
        description="Official institute invited visitors",
    )


@pytest.fixture
def sample_room(db):
    return Room.objects.create(
        room_number="101",
        room_type="NON_SUITE",
        occupancy_type="DOUBLE",
        floor=1,
        status=RoomStatus.AVAILABLE,
    )


@pytest.fixture
def sample_tariff(db, visitor_category):
    return Tariff.objects.create(
        category=visitor_category,
        room_type="NON_SUITE",
        occupancy_type="DOUBLE",
        rate_per_day=Decimal("1000.00"),
        effective_from=timezone.localdate(),
    )


@pytest.mark.django_db
class TestVHModelsAndContracts:
    def test_model_creation(self, visitor_category, sample_room, sample_tariff):
        assert visitor_category.code == "A"
        assert sample_room.room_number == "101"
        assert sample_tariff.rate_per_day == Decimal("1000.00")

    def test_plural_contracts(self, visitor_category, sample_room):
        Booking.objects.create(
            indenter_id=42,
            visitor_name="Prof. Sharma",
            visitor_category=visitor_category,
            visit_purpose="Keynote Lecture",
            check_in_date=timezone.localdate() + timedelta(days=2),
            check_out_date=timezone.localdate() + timedelta(days=4),
            number_of_rooms=1,
        )

        user_bookings = contracts.get_bookings_for_users([42])
        assert len(user_bookings) == 1
        assert user_bookings[0]["visitor_name"] == "Prof. Sharma"

        rooms_info = contracts.get_rooms_by_ids([sample_room.id])
        assert len(rooms_info) == 1
        assert rooms_info[0]["room_number"] == "101"

    def test_inventory_threshold_alert(self, db):
        item = InventoryItem.objects.create(
            name="Bed Sheets",
            category="LINEN",
            current_quantity=5,
            minimum_threshold=10,
        )
        assert item.is_below_threshold is True


@pytest.mark.django_db
class TestBookingWorkflowAPI:
    def test_booking_lifecycle_progression(
        self, api_client, visitor_category, sample_room, sample_tariff
    ):
        """Test BW-VH-02, CW-VH-01, and BW-VH-10 workflow progression."""
        today = timezone.localdate()
        create_resp = api_client.post(
            "/api/v1/vh/bookings/",
            {
                "indenter_id": 10,
                "visitor_name": "Dr. APJ Visitor",
                "visitor_category": visitor_category.id,
                "visit_purpose": "Conference",
                "check_in_date": str(today + timedelta(days=1)),
                "check_out_date": str(today + timedelta(days=3)),
                "number_of_rooms": 1,
            },
            format="json",
        )
        assert create_resp.status_code == 201
        booking_id = create_resp.data["id"]
        assert create_resp.data["status"] == BookingStatus.PENDING

        # Step 1: Caretaker forwards to In-Charge (BW-VH-02)
        fwd_resp = api_client.post(
            f"/api/v1/vh/bookings/{booking_id}/forward/",
            {"remarks": "Rooms available, forwarding for approval."},
            format="json",
        )
        assert fwd_resp.status_code == 200
        assert fwd_resp.data["status"] == BookingStatus.FORWARDED

        # Step 2: In-Charge approves booking (CW-VH-01)
        app_resp = api_client.post(
            f"/api/v1/vh/bookings/{booking_id}/approve/",
            {"remarks": "Approved by VH In-Charge."},
            format="json",
        )
        assert app_resp.status_code == 200
        assert app_resp.data["status"] == BookingStatus.APPROVED

        # Step 3: Caretaker allots room (BR-VH-012, BW-VH-10)
        allot_resp = api_client.post(
            f"/api/v1/vh/bookings/{booking_id}/allot_room/",
            {"room_ids": [sample_room.id]},
            format="json",
        )
        assert allot_resp.status_code == 200
        assert allot_resp.data["booking"]["status"] == BookingStatus.ROOM_ALLOTTED

        # Step 4: Guest Check-in (BW-VH-10)
        ci_resp = api_client.post(f"/api/v1/vh/bookings/{booking_id}/check_in/")
        assert ci_resp.status_code == 200
        assert ci_resp.data["status"] == BookingStatus.CHECKED_IN

        # Step 5: Guest Check-out & Bill calculation (BW-VH-10, CFR-VH-011)
        co_resp = api_client.post(f"/api/v1/vh/bookings/{booking_id}/check_out/")
        assert co_resp.status_code == 200
        assert co_resp.data["booking"]["status"] == BookingStatus.CHECKED_OUT
        # 2 days stay @ 1000/day = 2000
        assert Decimal(co_resp.data["bill"]["room_charges"]) == Decimal("2000.00")

    def test_cancellation_7_days_prior_no_charge(
        self, api_client, visitor_category, sample_tariff
    ):
        """Test BR-VH-007: >= 7 days notice -> 0% charge."""
        today = timezone.localdate()
        create_resp = api_client.post(
            "/api/v1/vh/bookings/",
            {
                "indenter_id": 11,
                "visitor_name": "Early Guest",
                "visitor_category": visitor_category.id,
                "visit_purpose": "Meeting",
                "check_in_date": str(today + timedelta(days=10)),
                "check_out_date": str(today + timedelta(days=12)),
            },
            format="json",
        )
        booking_id = create_resp.data["id"]

        cancel_resp = api_client.post(
            f"/api/v1/vh/bookings/{booking_id}/cancel/",
            {"reason": "Event postponed"},
            format="json",
        )
        assert cancel_resp.status_code == 200
        assert cancel_resp.data["booking"]["status"] == BookingStatus.CANCELLED
        assert Decimal(cancel_resp.data["bill"]["cancellation_charges"]) == Decimal("0.00")

    def test_cancellation_within_7_days_charge(
        self, api_client, visitor_category, sample_tariff
    ):
        """Test BR-VH-008: within 7 days -> 25% charge of 1-day room rent."""
        today = timezone.localdate()
        create_resp = api_client.post(
            "/api/v1/vh/bookings/",
            {
                "indenter_id": 12,
                "visitor_name": "Late Guest",
                "visitor_category": visitor_category.id,
                "visit_purpose": "Workshop",
                "check_in_date": str(today + timedelta(days=3)),
                "check_out_date": str(today + timedelta(days=5)),
            },
            format="json",
        )
        booking_id = create_resp.data["id"]

        cancel_resp = api_client.post(
            f"/api/v1/vh/bookings/{booking_id}/cancel/",
            {"reason": "Plans changed"},
            format="json",
        )
        assert cancel_resp.status_code == 200
        assert cancel_resp.data["booking"]["status"] == BookingStatus.CANCELLED
        # Tariff is 1000/day. 25% of 1000 = 250.00
        assert Decimal(cancel_resp.data["bill"]["cancellation_charges"]) == Decimal("250.00")
