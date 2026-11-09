"""Exhaustive integration test matrix covering categories, room types, tariffs, durations, cancellations, and availability."""
from datetime import timedelta
from decimal import Decimal
import pytest
from django.utils import timezone

from modules.vh.models import (
    Booking,
    BookingStatus,
    InventoryCategory,
    InventoryItem,
    OccupancyType,
    OfflineBookingType,
    Room,
    RoomAllotment,
    RoomStatus,
    RoomType,
    Tariff,
    VisitorCategory,
)


@pytest.mark.django_db
class TestBillingCheckoutMatrix:
    """Matrix of 64 integration tests: 4 Categories x 2 Room Types x 2 Occupancies x 4 Stay Durations."""

    @pytest.mark.parametrize("cat_code", ["A", "B", "C", "D"])
    @pytest.mark.parametrize("r_type", [RoomType.SUITE, RoomType.NON_SUITE])
    @pytest.mark.parametrize("occ", [OccupancyType.SINGLE, OccupancyType.DOUBLE])
    @pytest.mark.parametrize("days", [1, 2, 3, 5])
    def test_end_to_end_stay_billing(
        self, api_client, all_categories, all_room_combinations, all_tariffs, cat_code, r_type, occ, days
    ):
        today = timezone.localdate()
        cat = next(c for c in all_categories if c.code == cat_code)
        room = next(r for r in all_room_combinations if r.room_type == r_type and r.occupancy_type == occ)
        tariff = Tariff.objects.get(category=cat, room_type=r_type, occupancy_type=occ)

        # 1. Create booking
        b = Booking.objects.create(
            indenter_id=1,
            visitor_name=f"Matrix {cat_code}-{r_type[:2]}-{occ[:2]}-{days}d",
            visitor_category=cat,
            visit_purpose="Matrix Testing",
            check_in_date=today,
            check_out_date=today + timedelta(days=days),
            number_of_rooms=1,
            status=BookingStatus.APPROVED,
        )

        # 2. Allot room
        allot_resp = api_client.post(
            f"/api/v1/vh/bookings/{b.id}/allot_room/",
            {"room_ids": [room.id]},
            format="json",
        )
        assert allot_resp.status_code == 200

        # 3. Check in
        ci_resp = api_client.post(f"/api/v1/vh/bookings/{b.id}/check_in/")
        assert ci_resp.status_code == 200

        # 4. Check out
        co_resp = api_client.post(f"/api/v1/vh/bookings/{b.id}/check_out/")
        assert co_resp.status_code == 200
        expected_charges = tariff.rate_per_day * Decimal(str(days))
        assert Decimal(co_resp.data["bill"]["room_charges"]) == expected_charges
        assert Decimal(co_resp.data["bill"]["total_amount"]) == expected_charges


@pytest.mark.django_db
class TestCancellationMatrixAcrossCategories:
    """Matrix of 24 integration tests: 4 Categories x 3 Notice Windows x 2 Room Counts."""

    @pytest.mark.parametrize("cat_code", ["A", "B", "C", "D"])
    @pytest.mark.parametrize("days_notice,percent_mult", [
        (10, Decimal("0.00")),
        (3, Decimal("0.25")),
        (0, Decimal("0.50")),
    ])
    @pytest.mark.parametrize("rooms", [1, 2])
    def test_cancellation_matrix(
        self, api_client, all_categories, all_tariffs, cat_code, days_notice, percent_mult, rooms
    ):
        today = timezone.localdate()
        cat = next(c for c in all_categories if c.code == cat_code)
        # Fetch base tariff rate for category
        tariff = Tariff.objects.filter(category=cat).order_by("-effective_from").first()
        base_rate = tariff.rate_per_day

        b = Booking.objects.create(
            indenter_id=1,
            visitor_name=f"Cancel Matrix {cat_code}-{days_notice}d-{rooms}r",
            visitor_category=cat,
            visit_purpose="Matrix Cancel",
            check_in_date=today + timedelta(days=days_notice),
            check_out_date=today + timedelta(days=days_notice + 2),
            number_of_rooms=rooms,
        )

        req_resp = api_client.post(f"/api/v1/vh/bookings/{b.id}/request_cancellation/")
        assert req_resp.status_code == 200

        expected_charge = (base_rate * Decimal(str(rooms)) * percent_mult).quantize(Decimal("0.01"))
        assert Decimal(req_resp.data["applicable_cancellation_charge"]) == expected_charge

        conf_resp = api_client.post(f"/api/v1/vh/bookings/{b.id}/confirm_cancellation/")
        assert conf_resp.status_code == 200
        assert Decimal(conf_resp.data["bill"]["cancellation_charges"]) == expected_charge


@pytest.mark.django_db
class TestRoomAvailabilityIntervalMatrix:
    """Matrix of 12 tests: checking room availability across varied date overlapping intervals."""

    @pytest.mark.parametrize("q_in,q_out,expect_available", [
        (-10, -5, True),   # completely before booked stay
        (-5, 0, True),     # ends on check-in day (before stay)
        (-3, 2, False),    # overlaps start of booked stay
        (0, 5, False),     # exact match with booked stay
        (1, 3, False),     # inside booked stay
        (2, 7, False),     # overlaps end of booked stay
        (5, 10, True),     # starts on checkout day
        (6, 12, True),     # completely after booked stay
        (-2, 8, False),    # spans over entire booked stay
        (0, 1, False),     # inside start
        (4, 5, False),     # inside end
        (10, 15, True),    # far future
    ])
    def test_availability_overlap_intervals(
        self, api_client, category_a, sample_room, q_in, q_out, expect_available
    ):
        today = timezone.localdate()
        # Create an existing booked stay from today+0 to today+5
        booked = Booking.objects.create(
            indenter_id=1,
            visitor_name="Existing Guest",
            visitor_category=category_a,
            visit_purpose="Interval Check",
            check_in_date=today,
            check_out_date=today + timedelta(days=5),
            status=BookingStatus.ROOM_ALLOTTED,
        )
        RoomAllotment.objects.create(booking=booked, room=sample_room)

        query_in = today + timedelta(days=q_in)
        query_out = today + timedelta(days=q_out)
        resp = api_client.get(f"/api/v1/vh/rooms/availability/?check_in={query_in}&check_out={query_out}")
        assert resp.status_code == 200
        available_ids = {r["id"] for r in resp.data}
        if expect_available:
            assert sample_room.id in available_ids
        else:
            assert sample_room.id not in available_ids


@pytest.mark.django_db
class TestOfflineBookingCategoryMatrix:
    """Matrix of 16 tests: 2 Offline Types x 4 Categories x (Approved vs Rejected)."""

    @pytest.mark.parametrize("off_type", [OfflineBookingType.TELEPHONIC, OfflineBookingType.WALK_IN])
    @pytest.mark.parametrize("cat_code", ["A", "B", "C", "D"])
    @pytest.mark.parametrize("outcome", ["approve", "reject"])
    def test_offline_booking_matrix(self, api_client, all_categories, off_type, cat_code, outcome):
        today = timezone.localdate()
        cat = next(c for c in all_categories if c.code == cat_code)

        create_resp = api_client.post(
            "/api/v1/vh/bookings/",
            {
                "indenter_id": 1,
                "is_offline": True,
                "offline_booking_type": off_type,
                "visitor_name": f"Offline Matrix {cat_code}",
                "visitor_category": cat.id,
                "visit_purpose": "Matrix Purpose",
                "check_in_date": str(today),
                "check_out_date": str(today + timedelta(days=1)),
            },
            format="json",
        )
        assert create_resp.status_code == 201
        b_id = create_resp.data["id"]

        if outcome == "approve":
            api_client.post(f"/api/v1/vh/bookings/{b_id}/forward/")
            fin_resp = api_client.post(f"/api/v1/vh/bookings/{b_id}/approve/")
            assert fin_resp.status_code == 200
            assert fin_resp.data["status"] == BookingStatus.APPROVED
        else:
            fin_resp = api_client.post(f"/api/v1/vh/bookings/{b_id}/reject/")
            assert fin_resp.status_code == 200
            assert fin_resp.data["status"] == BookingStatus.REJECTED


@pytest.mark.django_db
class TestInventoryStockLevelsMatrix:
    """Matrix of 24 tests: 4 Inventory Categories x 6 stock level boundaries."""

    @pytest.mark.parametrize("cat", [
        InventoryCategory.LINEN,
        InventoryCategory.UTENSILS,
        InventoryCategory.CONSUMABLES,
        InventoryCategory.OTHERS,
    ])
    @pytest.mark.parametrize("qty,expected_alert", [
        (0, True),
        (1, True),
        (5, True),
        (9, True),
        (10, False),
        (20, False),
    ])
    def test_inventory_levels(self, api_client, cat, qty, expected_alert):
        resp = api_client.post(
            "/api/v1/vh/inventory/",
            {
                "name": f"Matrix Inv {cat}-{qty}",
                "category": cat,
                "current_quantity": qty,
                "minimum_threshold": 10,
            },
            format="json",
        )
        assert resp.status_code == 201
        assert resp.data["is_below_threshold"] is expected_alert


@pytest.mark.django_db
class TestBookingModificationVariations:
    """10 tests: modification requests across different field variations."""

    @pytest.mark.parametrize("delta_in,delta_out,new_rooms,new_occ", [
        (1, 0, None, None),
        (0, 2, None, None),
        (2, 4, None, None),
        (None, None, 2, None),
        (None, None, 3, None),
        (None, None, None, 2),
        (None, None, None, 4),
        (1, 2, 2, 2),
        (-1, 1, 3, 3),
        (0, 0, 1, 1),
    ])
    def test_modification_permutations(
        self, api_client, category_a, delta_in, delta_out, new_rooms, new_occ
    ):
        today = timezone.localdate()
        b = Booking.objects.create(
            indenter_id=1,
            visitor_name="Perm Mod Guest",
            visitor_category=category_a,
            visit_purpose="Perm Mod",
            check_in_date=today + timedelta(days=5),
            check_out_date=today + timedelta(days=7),
            number_of_rooms=1,
            number_of_occupants=1,
        )

        payload = {"booking": b.id, "reason": "Permutation change"}
        if delta_in is not None:
            payload["new_check_in_date"] = str(b.check_in_date + timedelta(days=delta_in))
        if delta_out is not None:
            payload["new_check_out_date"] = str(b.check_out_date + timedelta(days=delta_out))
        if new_rooms is not None:
            payload["new_number_of_rooms"] = new_rooms
        if new_occ is not None:
            payload["new_number_of_occupants"] = new_occ

        resp = api_client.post("/api/v1/vh/modifications/", payload, format="json")
        assert resp.status_code == 201
        mod_id = resp.data["id"]

        conf_resp = api_client.post(f"/api/v1/vh/modifications/{mod_id}/confirm/")
        assert conf_resp.status_code == 200


@pytest.mark.django_db
class TestPrintableSlipAllStatuses:
    """9 tests: verify printable slip generation across all booking statuses."""

    @pytest.mark.parametrize("status_val", [
        BookingStatus.PENDING,
        BookingStatus.FORWARDED,
        BookingStatus.APPROVED,
        BookingStatus.REJECTED,
        BookingStatus.ROOM_ALLOTTED,
        BookingStatus.CHECKED_IN,
        BookingStatus.CHECKED_OUT,
        BookingStatus.CANCELLATION_REQUESTED,
        BookingStatus.CANCELLED,
    ])
    def test_printable_slip_status_coverage(self, api_client, category_a, status_val):
        today = timezone.localdate()
        b = Booking.objects.create(
            indenter_id=1,
            visitor_name=f"Slip {status_val}",
            visitor_category=category_a,
            visit_purpose="Slip Verification",
            check_in_date=today,
            check_out_date=today + timedelta(days=2),
            status=status_val,
        )
        resp = api_client.get(f"/api/v1/vh/bookings/{b.id}/printable/")
        assert resp.status_code == 200
        assert resp.data["status"] == status_val
        assert resp.data["booking_reference"] == b.booking_reference

