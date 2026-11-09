"""Unit and API tests for the Visitors Hostel (VH) module."""
from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from modules.vh import contracts
from modules.vh.models import (
    Bill,
    Booking,
    BookingModification,
    BookingStatus,
    InventoryItem,
    InventoryReplenishment,
    MealAddOn,
    MealBooking,
    MealType,
    ModificationStatus,
    ReplenishmentStatus,
    Room,
    RoomAllotment,
    RoomStatus,
    Tariff,
    VHAlert,
    VHAlertType,
    VHNotificationLog,
    VisitorCategory,
    VHMSUserRole,
    VHMSUserRoleType,
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

        VHMSUserRole.objects.create(
            role_type=VHMSUserRoleType.CARETAKER,
            user_id=101,
            is_active=True,
        )
        roles_info = contracts.get_active_operational_roles([VHMSUserRoleType.CARETAKER])
        assert len(roles_info) == 1
        assert roles_info[0]["user_id"] == 101

        counts = contracts.get_pending_booking_counts_for_users([42])
        assert len(counts) == 1
        assert counts[0]["pending_count"] == 1

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

    def test_bw_vh_01_direct_rejection(self, api_client, visitor_category):
        """Test BW-VH-01: Caretaker rejects pending booking directly."""
        today = timezone.localdate()
        create_resp = api_client.post(
            "/api/v1/vh/bookings/",
            {
                "indenter_id": 20,
                "visitor_name": "Applicant Direct Reject",
                "visitor_category": visitor_category.id,
                "visit_purpose": "Personal",
                "check_in_date": str(today + timedelta(days=2)),
                "check_out_date": str(today + timedelta(days=3)),
            },
            format="json",
        )
        b_id = create_resp.data["id"]
        rej_resp = api_client.post(
            f"/api/v1/vh/bookings/{b_id}/reject/",
            {"remarks": "No rooms available."},
            format="json",
        )
        assert rej_resp.status_code == 200
        assert rej_resp.data["status"] == BookingStatus.REJECTED

    def test_bw_vh_03_forwarded_and_rejected(self, api_client, visitor_category):
        """Test BW-VH-03: Caretaker forwards, then In-Charge rejects."""
        today = timezone.localdate()
        create_resp = api_client.post(
            "/api/v1/vh/bookings/",
            {
                "indenter_id": 21,
                "visitor_name": "Applicant InCharge Reject",
                "visitor_category": visitor_category.id,
                "visit_purpose": "Official Meeting",
                "check_in_date": str(today + timedelta(days=5)),
                "check_out_date": str(today + timedelta(days=7)),
            },
            format="json",
        )
        b_id = create_resp.data["id"]
        api_client.post(f"/api/v1/vh/bookings/{b_id}/forward/", {"remarks": "Please decide."})
        rej_resp = api_client.post(
            f"/api/v1/vh/bookings/{b_id}/reject/",
            {"remarks": "Hostel reserved for institute summit."},
            format="json",
        )
        assert rej_resp.status_code == 200
        assert rej_resp.data["status"] == BookingStatus.REJECTED

    def test_offline_booking_workflows(self, api_client, visitor_category, sample_room):
        """Test BW-VH-04, 05, 06 & BR-VH-003, 005: Caretaker records telephonic/walk-in booking."""
        today = timezone.localdate()
        resp = api_client.post(
            "/api/v1/vh/bookings/",
            {
                "indenter_id": 1,
                "is_offline": True,
                "offline_booking_type": "WALK_IN",
                "visitor_name": "Walk-in Guest",
                "visitor_category": visitor_category.id,
                "visit_purpose": "Emergency stay",
                "check_in_date": str(today),
                "check_out_date": str(today + timedelta(days=1)),
            },
            format="json",
        )
        assert resp.status_code == 201
        assert resp.data["is_offline"] is True
        assert resp.data["offline_booking_type"] == "WALK_IN"
        assert resp.data["status"] == BookingStatus.PENDING

    def test_two_step_cancellation_workflow(
        self, api_client, visitor_category, sample_tariff
    ):
        """Test BW-VH-07..09 & CW-VH-02: Indenter requests, Caretaker confirms cancellation."""
        today = timezone.localdate()
        create_resp = api_client.post(
            "/api/v1/vh/bookings/",
            {
                "indenter_id": 15,
                "visitor_name": "Cancelling Guest",
                "visitor_category": visitor_category.id,
                "visit_purpose": "Symposium",
                "check_in_date": str(today + timedelta(days=4)),  # within 7 days -> 25% charge
                "check_out_date": str(today + timedelta(days=6)),
            },
            format="json",
        )
        booking_id = create_resp.data["id"]

        # Step 1: Indenter requests cancellation (UC-VH-007)
        req_resp = api_client.post(
            f"/api/v1/vh/bookings/{booking_id}/request_cancellation/",
            {"reason": "Flight cancelled"},
            format="json",
        )
        assert req_resp.status_code == 200
        assert req_resp.data["booking"]["status"] == BookingStatus.CANCELLATION_REQUESTED
        # Tariff is 1000/day, 25% of 1000 = 250.00
        assert Decimal(req_resp.data["applicable_cancellation_charge"]) == Decimal("250.00")

        # Step 2: Caretaker reviews & confirms cancellation (UC-VH-020, CW-VH-02)
        confirm_resp = api_client.post(
            f"/api/v1/vh/bookings/{booking_id}/confirm_cancellation/",
            format="json",
        )
        assert confirm_resp.status_code == 200
        assert confirm_resp.data["booking"]["status"] == BookingStatus.CANCELLED
        assert Decimal(confirm_resp.data["bill"]["cancellation_charges"]) == Decimal("250.00")

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
        assert Decimal(cancel_resp.data["bill"]["cancellation_charges"]) == Decimal("250.00")

    def test_printable_booking_slip(self, api_client, visitor_category):
        """Test UC-VH-002, AFR-VH-003: Printable booking details endpoint."""
        today = timezone.localdate()
        create_resp = api_client.post(
            "/api/v1/vh/bookings/",
            {
                "indenter_id": 99,
                "visitor_name": "Printable Guest",
                "visitor_category": visitor_category.id,
                "visit_purpose": "Convocation",
                "check_in_date": str(today + timedelta(days=5)),
                "check_out_date": str(today + timedelta(days=6)),
            },
            format="json",
        )
        b_id = create_resp.data["id"]
        slip_resp = api_client.get(f"/api/v1/vh/bookings/{b_id}/printable/")
        assert slip_resp.status_code == 200
        assert "Visitors Hostel Booking Slip" in slip_resp.data["title"]
        assert slip_resp.data["visitor_name"] == "Printable Guest"


@pytest.mark.django_db
class TestBookingModificationsAPI:
    def test_modification_request_and_confirmation(
        self, api_client, visitor_category, sample_tariff
    ):
        """Test UC-VH-006, UC-VH-022, BR-VH-010: Request modification and confirm outcome."""
        today = timezone.localdate()
        booking = Booking.objects.create(
            indenter_id=1,
            visitor_name="Modifiable Guest",
            visitor_category=visitor_category,
            visit_purpose="Research Visit",
            check_in_date=today + timedelta(days=5),
            check_out_date=today + timedelta(days=7),
            number_of_rooms=1,
        )

        # 1. Indenter requests modification before arrival (UC-VH-006)
        mod_resp = api_client.post(
            "/api/v1/vh/modifications/",
            {
                "booking": booking.id,
                "new_check_in_date": str(today + timedelta(days=6)),
                "new_check_out_date": str(today + timedelta(days=9)),
                "new_number_of_rooms": 2,
                "reason": "Team size increased",
            },
            format="json",
        )
        assert mod_resp.status_code == 201
        mod_id = mod_resp.data["id"]
        assert mod_resp.data["status"] == ModificationStatus.PENDING

        # 2. Authority confirms modification outcome (UC-VH-022, BR-VH-010)
        confirm_resp = api_client.post(
            f"/api/v1/vh/modifications/{mod_id}/confirm/",
            {"remarks": "Approved by authority."},
            format="json",
        )
        assert confirm_resp.status_code == 200
        assert confirm_resp.data["status"] == ModificationStatus.CONFIRMED

        booking.refresh_from_db()
        assert booking.check_in_date == today + timedelta(days=6)
        assert booking.check_out_date == today + timedelta(days=9)
        assert booking.number_of_rooms == 2

    def test_modification_rejection(self, api_client, visitor_category):
        today = timezone.localdate()
        booking = Booking.objects.create(
            indenter_id=1,
            visitor_name="Reject Mod Guest",
            visitor_category=visitor_category,
            visit_purpose="Guest Talk",
            check_in_date=today + timedelta(days=3),
            check_out_date=today + timedelta(days=4),
        )
        mod_resp = api_client.post(
            "/api/v1/vh/modifications/",
            {
                "booking": booking.id,
                "new_number_of_rooms": 5,
                "reason": "Need 5 rooms",
            },
            format="json",
        )
        mod_id = mod_resp.data["id"]
        rej_resp = api_client.post(
            f"/api/v1/vh/modifications/{mod_id}/reject/",
            {"remarks": "Hostel at capacity."},
            format="json",
        )
        assert rej_resp.status_code == 200
        assert rej_resp.data["status"] == ModificationStatus.REJECTED


@pytest.mark.django_db
class TestMealBookingsAPI:
    def test_meal_booking_validation_rules(self, api_client, visitor_category):
        """Test BR-VH-025, BR-VH-029, BR-VH-030, BR-VH-031."""
        today = timezone.localdate()
        booking = Booking.objects.create(
            indenter_id=1,
            visitor_name="Meal Guest",
            visitor_category=visitor_category,
            visit_purpose="Workshop",
            check_in_date=today,
            check_out_date=today + timedelta(days=3),
            status=BookingStatus.PENDING,  # not checked in yet!
        )

        # BR-VH-025: Must be checked in
        resp1 = api_client.post(
            "/api/v1/vh/meals/",
            {
                "booking": booking.id,
                "date": str(today + timedelta(days=1)),
                "meal_type": MealType.LUNCH,
                "add_on": MealAddOn.TEA,
                "number_of_persons": 1,
            },
            format="json",
        )
        assert resp1.status_code == 400
        assert "BR-VH-025" in str(resp1.data)

        # Set booking to checked-in
        booking.status = BookingStatus.CHECKED_IN
        booking.save()

        # BR-VH-031: Meal date must be within stay duration
        resp2 = api_client.post(
            "/api/v1/vh/meals/",
            {
                "booking": booking.id,
                "date": str(today + timedelta(days=10)),  # outside stay
                "meal_type": MealType.DINNER,
                "number_of_persons": 1,
            },
            format="json",
        )
        assert resp2.status_code == 400
        assert "BR-VH-031" in str(resp2.data)

        # Valid meal booking
        resp3 = api_client.post(
            "/api/v1/vh/meals/",
            {
                "booking": booking.id,
                "date": str(today + timedelta(days=1)),
                "meal_type": MealType.BREAKFAST,
                "add_on": MealAddOn.MILK,
                "number_of_persons": 2,
                "rate": "150.00",
            },
            format="json",
        )
        assert resp3.status_code == 201
        assert Decimal(resp3.data["total_amount"]) == Decimal("300.00")


@pytest.mark.django_db
class TestBillImmutabilityAndSettlementAPI:
    def test_settle_bill_offline_cash_and_immutability(self, api_client, visitor_category):
        """Test BR-VH-036, BR-VH-037: Cash settlement and immutability of finalized bills."""
        booking = Booking.objects.create(
            indenter_id=1,
            visitor_name="Billed Guest",
            visitor_category=visitor_category,
            visit_purpose="Exam Duty",
            check_in_date=timezone.localdate(),
            check_out_date=timezone.localdate() + timedelta(days=1),
            status=BookingStatus.CHECKED_OUT,
        )
        bill = Bill.objects.create(
            booking=booking,
            room_charges=Decimal("1000.00"),
            total_amount=Decimal("1000.00"),
        )

        # Settle bill (BR-VH-036)
        settle_resp = api_client.post(
            f"/api/v1/vh/bills/{bill.id}/settle/",
            {"guest_verification_notes": "Paid Rs 1000 cash at counter."},
            format="json",
        )
        assert settle_resp.status_code == 200
        assert settle_resp.data["is_settled"] is True
        assert settle_resp.data["is_finalized"] is True

        # Attempt to mutate finalized bill (BR-VH-037)
        mutate_resp = api_client.patch(
            f"/api/v1/vh/bills/{bill.id}/",
            {"room_charges": "500.00"},
            format="json",
        )
        assert mutate_resp.status_code == 400
        assert "BR-VH-037" in str(mutate_resp.data)

        # Attempt to delete finalized bill (BR-VH-037)
        del_resp = api_client.delete(f"/api/v1/vh/bills/{bill.id}/")
        assert del_resp.status_code == 400


@pytest.mark.django_db
class TestOperationalRoleManagementAPI:
    def test_reassign_roles_and_transfer_records(self, api_client, visitor_category):
        """Test BR-VH-045..050 & UC-VH-019: Single active role & immediate record transfer."""
        today = timezone.localdate()

        # Create bookings in various statuses
        b1 = Booking.objects.create(
            indenter_id=1,
            visitor_name="Pending Guest",
            visitor_category=visitor_category,
            visit_purpose="P1",
            check_in_date=today + timedelta(days=1),
            check_out_date=today + timedelta(days=2),
            status=BookingStatus.PENDING,
        )
        b2 = Booking.objects.create(
            indenter_id=2,
            visitor_name="Forwarded Guest",
            visitor_category=visitor_category,
            visit_purpose="P2",
            check_in_date=today + timedelta(days=2),
            check_out_date=today + timedelta(days=3),
            status=BookingStatus.FORWARDED,
        )

        # Assign Caretaker 1
        resp1 = api_client.post(
            "/api/v1/vh/roles/assign/",
            {"role_type": "CARETAKER", "user_id": 501},
            format="json",
        )
        assert resp1.status_code == 201
        assert resp1.data["is_active"] is True
        b1.refresh_from_db()
        assert b1.assigned_caretaker_id == 501

        # Reassign Caretaker to user 502 (BR-VH-045, BR-VH-048, BR-VH-049)
        resp2 = api_client.post(
            "/api/v1/vh/roles/assign/",
            {"role_type": "CARETAKER", "user_id": 502},
            format="json",
        )
        assert resp2.status_code == 201

        # Check user 501 role is deactivated (BR-VH-045: exactly one active)
        old_role = VHMSUserRole.objects.get(id=resp1.data["id"])
        assert old_role.is_active is False

        # Check records transferred to user 502 (BR-VH-049)
        b1.refresh_from_db()
        assert b1.assigned_caretaker_id == 502

        # Assign VH In-Charge to user 601 (BR-VH-046, BR-VH-050)
        resp3 = api_client.post(
            "/api/v1/vh/roles/assign/",
            {"role_type": "IN_CHARGE", "user_id": 601},
            format="json",
        )
        assert resp3.status_code == 201
        b2.refresh_from_db()
        assert b2.assigned_incharge_id == 601

        # Check active endpoint
        active_resp = api_client.get("/api/v1/vh/roles/active/")
        assert active_resp.status_code == 200
        assert active_resp.data["caretaker"]["user_id"] == 502
        assert active_resp.data["incharge"]["user_id"] == 601


@pytest.mark.django_db
class TestVHReportsAPI:
    def test_incharge_and_caretaker_reports(self, api_client, visitor_category, sample_room):
        """Test UC-VH-017 & UC-VH-018: In-Charge and Caretaker reports."""
        today = timezone.localdate()
        Booking.objects.create(
            indenter_id=1,
            visitor_name="Report Guest",
            visitor_category=visitor_category,
            visit_purpose="Meeting",
            check_in_date=today,
            check_out_date=today + timedelta(days=2),
            status=BookingStatus.APPROVED,
        )

        incharge_resp = api_client.get("/api/v1/vh/reports/incharge/")
        assert incharge_resp.status_code == 200
        assert "booking_summary" in incharge_resp.data
        assert "category_occupancy" in incharge_resp.data
        assert "revenue_summary" in incharge_resp.data
        assert "inventory_usage" in incharge_resp.data

        caretaker_resp = api_client.get("/api/v1/vh/reports/caretaker/")
        assert caretaker_resp.status_code == 200
        assert "daily_occupancy" in caretaker_resp.data
        assert "upcoming_arrivals" in caretaker_resp.data
        assert "pending_actions" in caretaker_resp.data
        assert "no_show_logs" in caretaker_resp.data


@pytest.mark.django_db
class TestAlertsAndNotificationsAPI:
    def test_stay_exceptions_scan_and_threshold_alerts(self, api_client, visitor_category, sample_room):
        """Test BR-VH-017, BR-VH-018, BR-VH-041, BR-VH-043, UC-VH-024, UC-VH-025."""
        today = timezone.localdate()

        # No-show condition: check_in_date past, room allotted, not checked in
        b_noshow = Booking.objects.create(
            indenter_id=1,
            visitor_name="No Show Guest",
            visitor_category=visitor_category,
            visit_purpose="Visit",
            check_in_date=today - timedelta(days=1),
            check_out_date=today + timedelta(days=1),
            status=BookingStatus.ROOM_ALLOTTED,
        )
        RoomAllotment.objects.create(booking=b_noshow, room=sample_room)

        # Inventory item below threshold
        item = InventoryItem.objects.create(
            name="Hand Soap",
            category="CONSUMABLES",
            current_quantity=2,
            minimum_threshold=10,
        )

        # Trigger scan
        scan_resp = api_client.post("/api/v1/vh/alerts/scan/")
        assert scan_resp.status_code == 200
        assert scan_resp.data["no_shows_detected"] >= 1

        # Verify alert created
        assert VHAlert.objects.filter(alert_type=VHAlertType.NO_SHOW).exists()
        assert VHAlert.objects.filter(alert_type=VHAlertType.INVENTORY_THRESHOLD).exists()

        # Verify notification logs recorded (UC-VH-023, BR-VH-043)
        notifs = api_client.get("/api/v1/vh/notifications/")
        assert notifs.status_code == 200
        assert len(notifs.data) >= 1

    def test_room_availability_endpoint(self, api_client, visitor_category, sample_room):
        """Test BR-VH-004, UC-VH-003: Room availability lookup."""
        today = timezone.localdate()
        resp = api_client.get(
            f"/api/v1/vh/rooms/availability/?check_in={today}&check_out={today + timedelta(days=2)}"
        )
        assert resp.status_code == 200
        assert any(r["room_number"] == "101" for r in resp.data)


@pytest.mark.django_db
class TestAdditionalEdgeCasesAndCoverage:
    def test_contracts_get_bills(self, visitor_category):
        booking = Booking.objects.create(
            indenter_id=1,
            visitor_name="Contract Guest",
            visitor_category=visitor_category,
            visit_purpose="Lecture",
            check_in_date=timezone.localdate(),
            check_out_date=timezone.localdate() + timedelta(days=1),
        )
        bill = Bill.objects.create(booking=booking, total_amount=Decimal("1200.00"))
        bills = contracts.get_bills_for_bookings([booking.id])
        assert len(bills) == 1
        assert bills[0]["total_amount"] == "1200.00"

    def test_workflow_error_branches(self, api_client, visitor_category, sample_room):
        today = timezone.localdate()
        booking = Booking.objects.create(
            indenter_id=1,
            visitor_name="Branch Guest",
            visitor_category=visitor_category,
            visit_purpose="Branch Check",
            check_in_date=today + timedelta(days=2),
            check_out_date=today + timedelta(days=4),
            status=BookingStatus.APPROVED,
        )

        # Cannot forward an already APPROVED booking
        fwd_err = api_client.post(f"/api/v1/vh/bookings/{booking.id}/forward/")
        assert fwd_err.status_code == 400

        # Cannot check in before room allotment
        ci_err = api_client.post(f"/api/v1/vh/bookings/{booking.id}/check_in/")
        assert ci_err.status_code == 400

        # Allot non-existent room
        allot_404 = api_client.post(
            f"/api/v1/vh/bookings/{booking.id}/allot_room/",
            {"room_ids": [99999]},
            format="json",
        )
        assert allot_404.status_code == 404

        # Allot room with empty list
        allot_empty = api_client.post(
            f"/api/v1/vh/bookings/{booking.id}/allot_room/",
            {"room_ids": []},
            format="json",
        )
        assert allot_empty.status_code == 400

        # Allot occupied room
        sample_room.status = RoomStatus.OCCUPIED
        sample_room.save()
        allot_occ = api_client.post(
            f"/api/v1/vh/bookings/{booking.id}/allot_room/",
            {"room_ids": [sample_room.id]},
            format="json",
        )
        assert allot_occ.status_code == 400

        # Confirm cancellation error when status not CANCELLATION_REQUESTED
        confirm_err = api_client.post(f"/api/v1/vh/bookings/{booking.id}/confirm_cancellation/")
        assert confirm_err.status_code == 400

        # Invalid date format in room availability
        avail_err = api_client.get("/api/v1/vh/rooms/availability/?check_in=bad&check_out=date")
        assert avail_err.status_code == 400

    def test_overstay_alert_scan(self, api_client, visitor_category, sample_room):
        today = timezone.localdate()
        booking = Booking.objects.create(
            indenter_id=1,
            visitor_name="Overstay Guest",
            visitor_category=visitor_category,
            visit_purpose="Overstay Check",
            check_in_date=today - timedelta(days=5),
            check_out_date=today - timedelta(days=1),
            status=BookingStatus.CHECKED_IN,
        )
        allot = RoomAllotment.objects.create(
            booking=booking,
            room=sample_room,
            check_in_time=timezone.now() - timedelta(days=5),
        )
        scan_resp = api_client.post("/api/v1/vh/alerts/scan/")
        assert scan_resp.status_code == 200
        assert scan_resp.data["overstays_detected"] >= 1
        assert VHAlert.objects.filter(alert_type=VHAlertType.OVERSTAY).exists()

    def test_inventory_replenishment_flow(self, api_client):
        item = InventoryItem.objects.create(
            name="Bed Pillows",
            category="LINEN",
            current_quantity=4,
            minimum_threshold=10,
        )
        # Caretaker requests replenishment
        req_resp = api_client.post(
            f"/api/v1/vh/inventory/{item.id}/request_replenishment/",
            {"quantity_requested": 15, "remarks": "Low stock"},
            format="json",
        )
        assert req_resp.status_code == 201
        rep_id = req_resp.data["id"]

        # In-Charge approves replenishment
        app_resp = api_client.post(f"/api/v1/vh/replenishments/{rep_id}/approve/")
        assert app_resp.status_code == 200
        assert app_resp.data["status"] == ReplenishmentStatus.APPROVED
        item.refresh_from_db()
        assert item.current_quantity == 19

        # In-Charge rejects another replenishment
        rep2 = InventoryReplenishment.objects.create(
            item=item,
            quantity_requested=50,
            requested_by_user_id=1,
        )
        rej_resp = api_client.post(f"/api/v1/vh/replenishments/{rep2.id}/reject/")
        assert rej_resp.status_code == 200
        assert rej_resp.data["status"] == ReplenishmentStatus.REJECTED

    def test_alert_resolve(self, api_client):
        alert = VHAlert.objects.create(
            alert_type=VHAlertType.NO_SHOW,
            message="Test no show alert",
        )
        res_resp = api_client.post(f"/api/v1/vh/alerts/{alert.id}/resolve/")
        assert res_resp.status_code == 200
        assert res_resp.data["is_resolved"] is True
        alert.refresh_from_db()
        assert alert.is_resolved is True

    def test_role_assign_validation(self, api_client):
        # Missing fields
        r1 = api_client.post("/api/v1/vh/roles/assign/", {}, format="json")
        assert r1.status_code == 400

        # Invalid role type
        r2 = api_client.post(
            "/api/v1/vh/roles/assign/",
            {"role_type": "INVALID_ROLE", "user_id": 99},
            format="json",
        )
        assert r2.status_code == 400
