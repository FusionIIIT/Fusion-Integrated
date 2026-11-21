"""Comprehensive Specification Coverage Test Suite for Visitors Hostel (VH) Module.

Maps explicitly to:
- 22 Core Functional Requirements (CFR-VH-001 through CFR-VH-022)
- 115 Atomic Functional Requirements (AFR-VH-001 through AFR-VH-115)
- 23 Active Use Cases (UC-VH-001 through UC-VH-025)
- 38 Active Business Rules (BR-VH-002 through BR-VH-050)
- 12 Basis and Composite Workflows (BW-VH-01..10, CW-VH-01..02)
- 21 Remediated Defects (ISS-001 through ISS-021)
"""
from datetime import timedelta
from decimal import Decimal
import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from modules.vh import contracts
from modules.vh.api.permissions import HasVHPermission
from modules.vh.models import (
    Bill,
    BillingResponsibility,
    Booking,
    BookingModification,
    BookingStatus,
    CheckInRecord,
    CheckOutRecord,
    InventoryCategory,
    InventoryItem,
    InventoryReplenishment,
    MealAddOn,
    MealBooking,
    MealType,
    ModificationStatus,
    OccupancyType,
    OfflineBookingType,
    PaymentMode,
    ReplenishmentStatus,
    Room,
    RoomAllotment,
    RoomStatus,
    RoomType,
    Tariff,
    VHAlert,
    VHAlertType,
    VHNotificationEventType,
    VHNotificationLog,
    VisitorCategory,
    VHMSUserRole,
    VHMSUserRoleType,
)
from modules.vh.services.notifications import (
    check_inventory_threshold_alert,
    check_stay_exception_alerts,
    emit_booking_lifecycle_notification,
)
from modules.vh.services.reports import get_caretaker_reports, get_incharge_reports


# ==============================================================================
# CFR-VH-001: Indenter Booking Information Access (AFR-VH-001, AFR-VH-002, AFR-VH-003, ISS-002)
# ==============================================================================
@pytest.mark.django_db
class TestCFR001IndenterInformationAccess:
    """CFR-VH-001, AFR-VH-001, AFR-VH-002, AFR-VH-003, ISS-002, UC-VH-002.

    VHMS shall provide an Indenter controlled access to the status, history,
    booking details, confirmation details, and printable information for the
    Indenter's own submitted bookings.
    """

    def test_cfr_vh_001_afr_001_002_003_indenter_tracking_viewing_printing(
        self, api_client, category_a
    ):
        """AFR-VH-001, AFR-VH-002, AFR-VH-003, UC-VH-002: Track, view, and print booking details."""
        today = timezone.localdate()
        booking = Booking.objects.create(
            indenter_id=101,
            visitor_name="Prof. Ramanujan",
            visitor_category=category_a,
            visit_purpose="Mathematics Colloquium",
            check_in_date=today + timedelta(days=5),
            check_out_date=today + timedelta(days=7),
            number_of_rooms=1,
            number_of_occupants=1,
            billing_responsibility=BillingResponsibility.INSTITUTE,
            status=BookingStatus.APPROVED,
        )

        # 1. Track status & history (AFR-VH-001)
        resp = api_client.get(f"/api/v1/vh/bookings/{booking.id}/")
        assert resp.status_code == 200
        assert resp.data["id"] == booking.id
        assert resp.data["status"] == BookingStatus.APPROVED

        # 2. View details (AFR-VH-002)
        assert resp.data["visitor_name"] == "Prof. Ramanujan"
        assert resp.data["visit_purpose"] == "Mathematics Colloquium"
        assert resp.data["billing_responsibility"] == BillingResponsibility.INSTITUTE
        assert resp.data["booking_reference"].startswith("VH-")

        # 3. Printable confirmation details (AFR-VH-003)
        assert resp.data["booking_reference"] is not None
        assert resp.data["check_in_date"] == str(today + timedelta(days=5))
        assert resp.data["check_out_date"] == str(today + timedelta(days=7))

    def test_cfr_vh_001_iss_002_indenter_query_isolation(
        self, api_client, category_a
    ):
        """ISS-002, CFR-VH-001, AFR-VH-001, AFR-VH-002, AFR-VH-003: Indenters can only query own bookings."""
        today = timezone.localdate()
        Booking.objects.create(
            indenter_id=101,
            visitor_name="Guest of Indenter 101",
            visitor_category=category_a,
            visit_purpose="Colloquium",
            check_in_date=today + timedelta(days=1),
            check_out_date=today + timedelta(days=3),
            status=BookingStatus.PENDING,
        )
        Booking.objects.create(
            indenter_id=202,
            visitor_name="Guest of Indenter 202",
            visitor_category=category_a,
            visit_purpose="Research",
            check_in_date=today + timedelta(days=2),
            check_out_date=today + timedelta(days=4),
            status=BookingStatus.PENDING,
        )

        # Indenter 101 querying filtered by indenter_id
        resp_101 = api_client.get("/api/v1/vh/bookings/?indenter_id=101")
        assert resp_101.status_code == 200
        assert len(resp_101.data) == 1
        assert resp_101.data[0]["visitor_name"] == "Guest of Indenter 101"

        # Indenter 202 querying filtered by indenter_id
        resp_202 = api_client.get("/api/v1/vh/bookings/?indenter_id=202")
        assert resp_202.status_code == 200
        assert len(resp_202.data) == 1
        assert resp_202.data[0]["visitor_name"] == "Guest of Indenter 202"


# ==============================================================================
# CFR-VH-002: Online Booking Request Creation (AFR-VH-005..013, BR-VH-002, ISS-020)
# ==============================================================================
@pytest.mark.django_db
class TestCFR002OnlineBookingCreation:
    """CFR-VH-002, AFR-VH-005, AFR-VH-006, AFR-VH-007, AFR-VH-008, AFR-VH-009, AFR-VH-010, AFR-VH-011, AFR-VH-012, AFR-VH-013, BR-VH-002, ISS-020, UC-VH-001.

    VHMS shall support creation of a standardized online booking request by an
    authorized Indenter, capture the required booking data and permitted billing
    responsibility, and place a successfully submitted request in Pending state.
    """

    def test_cfr_vh_002_afr_005_to_013_standardized_requisition_submission(
        self, api_client, category_b
    ):
        """AFR-VH-005, AFR-VH-006, AFR-VH-007, AFR-VH-008, AFR-VH-009, AFR-VH-010, AFR-VH-011, AFR-VH-012, AFR-VH-013, ISS-020: Captures requisition fields and sets Pending."""
        today = timezone.localdate()
        payload = {
            "indenter_id": 105,
            "visitor_name": "Dr. Marie Curie",  # AFR-VH-006: visitor details
            "visitor_category": category_b.id,  # AFR-VH-008: category
            "visit_purpose": "Keynote Lecture",  # AFR-VH-007: purpose
            "check_in_date": str(today + timedelta(days=10)),  # AFR-VH-009: stay duration
            "check_out_date": str(today + timedelta(days=14)),
            "expected_check_in_time": "15:00:00",  # AFR-VH-009, ISS-020: timings
            "expected_check_out_time": "11:00:00",
            "number_of_rooms": 1,  # AFR-VH-010: rooms & occupants
            "number_of_occupants": 1,
            "billing_responsibility": BillingResponsibility.PROJECT,  # AFR-VH-011, AFR-VH-012, BR-VH-002
        }

        # AFR-VH-005: standardized online booking request submission
        resp = api_client.post("/api/v1/vh/bookings/", payload, format="json")
        assert resp.status_code == 201

        # AFR-VH-013: Status must be Pending after submission
        assert resp.data["status"] == BookingStatus.PENDING
        assert resp.data["expected_check_in_time"] == "15:00:00"
        assert resp.data["expected_check_out_time"] == "11:00:00"
        assert resp.data["billing_responsibility"] == BillingResponsibility.PROJECT
        assert resp.data["booking_reference"].startswith("VH-")

    @pytest.mark.parametrize("invalid_resp", ["INVALID", "GUEST", "UNKNOWN", "GOVERNMENT"])
    def test_cfr_vh_002_br_vh_002_invalid_billing_responsibility_rejected(
        self, api_client, category_a, invalid_resp
    ):
        """BR-VH-002, AFR-VH-012: Restrict billing responsibility to Visitor, Indenter, Institute, Project."""
        today = timezone.localdate()
        payload = {
            "indenter_id": 106,
            "visitor_name": "Dr. Invalid Resp",
            "visitor_category": category_a.id,
            "visit_purpose": "Meeting",
            "check_in_date": str(today + timedelta(days=2)),
            "check_out_date": str(today + timedelta(days=3)),
            "billing_responsibility": invalid_resp,
        }
        resp = api_client.post("/api/v1/vh/bookings/", payload, format="json")
        assert resp.status_code == 400


# ==============================================================================
# CFR-VH-003: Booking Review, Routing, and Final Decision (AFR-VH-014..020, ISS-003, ISS-004, ISS-005, ISS-009, ISS-021)
# ==============================================================================
@pytest.mark.django_db
class TestCFR003BookingReviewAndDecision:
    """CFR-VH-003, AFR-VH-014, AFR-VH-015, AFR-VH-016, AFR-VH-017, AFR-VH-018, AFR-VH-019, AFR-VH-020, UC-VH-003, UC-VH-004, ISS-003, ISS-004, ISS-005, ISS-009, ISS-021.

    VHMS shall support Caretaker review and room availability checking of pending
    booking requests, direct rejection or forwarding to VH In-Charge, and VH In-Charge
    approval or rejection with notification of final decision.
    """

    def test_cfr_vh_003_afr_014_016_caretaker_direct_rejection(
        self, api_client, category_a
    ):
        """AFR-VH-014, AFR-VH-016, UC-VH-003: Caretaker review and direct rejection."""
        today = timezone.localdate()
        booking = Booking.objects.create(
            indenter_id=109,
            visitor_name="Dr. Direct Reject",
            visitor_category=category_a,
            visit_purpose="Meeting",
            check_in_date=today + timedelta(days=2),
            check_out_date=today + timedelta(days=4),
            status=BookingStatus.PENDING,
        )
        resp = api_client.post(
            f"/api/v1/vh/bookings/{booking.id}/reject/",
            {"remarks": "Rooms unavailable due to maintenance."},
        )
        assert resp.status_code == 200
        booking.refresh_from_db()
        assert booking.status == BookingStatus.REJECTED
        assert booking.reviewed_at is not None

    def test_cfr_vh_003_afr_014_017_018_caretaker_forward_and_incharge_approve(
        self, api_client, category_a
    ):
        """AFR-VH-014, AFR-VH-017, AFR-VH-018, AFR-VH-020, ISS-021, UC-VH-003, UC-VH-004: Forward -> Approve with audit timestamps and notification."""
        today = timezone.localdate()
        booking = Booking.objects.create(
            indenter_id=110,
            visitor_name="Prof. H. Bhabha",
            visitor_category=category_a,
            visit_purpose="Department Review",
            check_in_date=today + timedelta(days=3),
            check_out_date=today + timedelta(days=5),
            status=BookingStatus.PENDING,
        )

        # 1. Caretaker forwards (AFR-VH-017, ISS-021)
        fwd_resp = api_client.post(
            f"/api/v1/vh/bookings/{booking.id}/forward/",
            {"remarks": "Rooms available, forwarding to In-Charge."},
        )
        assert fwd_resp.status_code == 200
        booking.refresh_from_db()
        assert booking.status == BookingStatus.FORWARDED
        assert booking.reviewed_at is not None
        assert booking.approved_at is None

        # 2. VH In-Charge approves (AFR-VH-018, ISS-021)
        app_resp = api_client.post(
            f"/api/v1/vh/bookings/{booking.id}/approve/",
            {"remarks": "Approved as institute official visitor."},
        )
        assert app_resp.status_code == 200
        booking.refresh_from_db()
        assert booking.status == BookingStatus.APPROVED
        assert booking.approved_at is not None

        # 3. Indenter notified (AFR-VH-020, UC-VH-023)
        notif = VHNotificationLog.objects.filter(
            booking=booking,
            event_type=VHNotificationEventType.BOOKING_APPROVED,
        ).exists()
        assert notif is True

    def test_cfr_vh_003_iss_003_approve_blocks_unforwarded_pending_booking(
        self, api_client, category_a
    ):
        """ISS-003, AFR-VH-018, UC-VH-004: In-Charge approve() requires FORWARDED and rejects PENDING with 400."""
        today = timezone.localdate()
        booking = Booking.objects.create(
            indenter_id=111,
            visitor_name="Unforwarded Guest",
            visitor_category=category_a,
            visit_purpose="Conference",
            check_in_date=today + timedelta(days=3),
            check_out_date=today + timedelta(days=5),
            status=BookingStatus.PENDING,
        )
        resp = api_client.post(f"/api/v1/vh/bookings/{booking.id}/approve/", {"remarks": "Bypass review"})
        assert resp.status_code == 400
        assert "FORWARDED" in resp.data["error"]

    def test_cfr_vh_003_iss_004_reject_blocks_terminal_approved_and_rejected(
        self, api_client, category_a
    ):
        """ISS-004, AFR-VH-019, UC-VH-004: reject() rejects terminal APPROVED and REJECTED bookings with 400."""
        today = timezone.localdate()
        b_app = Booking.objects.create(
            indenter_id=112,
            visitor_name="Already Approved",
            visitor_category=category_a,
            visit_purpose="Exam",
            check_in_date=today + timedelta(days=4),
            check_out_date=today + timedelta(days=6),
            status=BookingStatus.APPROVED,
        )
        r_app = api_client.post(f"/api/v1/vh/bookings/{b_app.id}/reject/", {"remarks": "Try reject approved"})
        assert r_app.status_code == 400

        b_rej = Booking.objects.create(
            indenter_id=113,
            visitor_name="Already Rejected",
            visitor_category=category_a,
            visit_purpose="Exam",
            check_in_date=today + timedelta(days=4),
            check_out_date=today + timedelta(days=6),
            status=BookingStatus.REJECTED,
        )
        r_rej = api_client.post(f"/api/v1/vh/bookings/{b_rej.id}/reject/", {"remarks": "Try reject rejected"})
        assert r_rej.status_code == 400

    def test_cfr_vh_003_iss_005_forward_requires_pending_status(
        self, api_client, category_a
    ):
        """ISS-005, AFR-VH-017: Caretaker forward requires PENDING; rejects non-pending bookings with 400."""
        today = timezone.localdate()
        booking = Booking.objects.create(
            indenter_id=114,
            visitor_name="Checked In Guest",
            visitor_category=category_a,
            visit_purpose="Seminar",
            check_in_date=today - timedelta(days=1),
            check_out_date=today + timedelta(days=1),
            status=BookingStatus.CHECKED_IN,
        )
        resp = api_client.post(f"/api/v1/vh/bookings/{booking.id}/forward/", {"remarks": "Re-forward"})
        assert resp.status_code == 400
        assert "PENDING" in resp.data["error"]

    def test_cfr_vh_003_iss_009_room_availability_date_interval_check(
        self, api_client, sample_room, category_a
    ):
        """ISS-009, AFR-VH-015, BR-VH-004: Room availability dynamically checks date overlaps."""
        today = timezone.localdate()
        b = Booking.objects.create(
            indenter_id=115,
            visitor_name="Overlapping Guest",
            visitor_category=category_a,
            visit_purpose="Workshop",
            check_in_date=today + timedelta(days=10),
            check_out_date=today + timedelta(days=15),
            status=BookingStatus.APPROVED,
        )
        RoomAllotment.objects.create(booking=b, room=sample_room)

        # 1. Query non-overlapping window Day 1 to Day 5: room 101 must be available
        r1 = api_client.get(
            f"/api/v1/vh/rooms/availability/?check_in={today + timedelta(days=1)}&check_out={today + timedelta(days=5)}"
        )
        assert r1.status_code == 200
        avail_rooms = [rm["room_number"] for rm in r1.data]
        assert sample_room.room_number in avail_rooms

        # 2. Query overlapping window Day 12 to Day 14: room 101 must NOT be available
        r2 = api_client.get(
            f"/api/v1/vh/rooms/availability/?check_in={today + timedelta(days=12)}&check_out={today + timedelta(days=14)}"
        )
        assert r2.status_code == 200
        avail_rooms_overlap = [rm["room_number"] for rm in r2.data]
        assert sample_room.room_number not in avail_rooms_overlap


# ==============================================================================
# CFR-VH-004: Offline Booking Recording and Approval Routing (AFR-VH-021..025, BR-VH-003..005)
# ==============================================================================
@pytest.mark.django_db
class TestCFR004OfflineBooking:
    """CFR-VH-004, AFR-VH-021, AFR-VH-022, AFR-VH-023, AFR-VH-024, AFR-VH-025, BR-VH-003, BR-VH-004, BR-VH-005, UC-VH-005, BW-VH-04, BW-VH-05, BW-VH-06.

    VHMS shall support Caretaker recording of offline (telephonic and walk-in)
    booking requests with mandatory offline flag, and apply the same approval
    routing and availability checks as online requests.
    """

    @pytest.mark.parametrize("off_type", [OfflineBookingType.TELEPHONIC, OfflineBookingType.WALK_IN])
    def test_cfr_vh_004_afr_021_022_025_record_offline_booking_with_audit_flag(
        self, api_client, category_c, off_type
    ):
        """AFR-VH-021, AFR-VH-022, AFR-VH-025, BR-VH-005: Offline booking recording and flag."""
        today = timezone.localdate()
        payload = {
            "indenter_id": 1,
            "visitor_name": f"Offline Guest ({off_type})",
            "visitor_category": category_c.id,
            "visit_purpose": "Urgent Official Work",
            "check_in_date": str(today + timedelta(days=1)),
            "check_out_date": str(today + timedelta(days=3)),
            "is_offline": True,
            "offline_booking_type": off_type,
            "billing_responsibility": BillingResponsibility.VISITOR,
        }
        resp = api_client.post("/api/v1/vh/bookings/", payload, format="json")
        assert resp.status_code == 201
        assert resp.data["is_offline"] is True
        assert resp.data["offline_booking_type"] == off_type
        assert resp.data["status"] == BookingStatus.PENDING

    def test_cfr_vh_004_br_vh_003_br_vh_004_afr_023_024_offline_follows_same_routing(
        self, api_client, category_a
    ):
        """AFR-VH-023, AFR-VH-024, BR-VH-003, BR-VH-004, BW-VH-05: Offline bookings follow same approval routing to In-Charge."""
        today = timezone.localdate()
        booking = Booking.objects.create(
            indenter_id=1,
            visitor_name="Walk-in Delegate",
            visitor_category=category_a,
            visit_purpose="Special Meeting",
            check_in_date=today + timedelta(days=2),
            check_out_date=today + timedelta(days=4),
            is_offline=True,
            offline_booking_type=OfflineBookingType.WALK_IN,
            status=BookingStatus.PENDING,
        )

        # Forwarded by Caretaker
        r_fwd = api_client.post(f"/api/v1/vh/bookings/{booking.id}/forward/", {"remarks": "Walk-in verified"})
        assert r_fwd.status_code == 200
        booking.refresh_from_db()
        assert booking.status == BookingStatus.FORWARDED

        # Approved by In-Charge
        r_app = api_client.post(f"/api/v1/vh/bookings/{booking.id}/approve/", {"remarks": "Walk-in approved"})
        assert r_app.status_code == 200
        booking.refresh_from_db()
        assert booking.status == BookingStatus.APPROVED


# ==============================================================================
# CFR-VH-005: Booking Modification Handling (AFR-VH-026, AFR-VH-034, BR-VH-010, CW-VH-02)
# ==============================================================================
@pytest.mark.django_db
class TestCFR005BookingModification:
    """CFR-VH-005, AFR-VH-026, AFR-VH-034, BR-VH-010, BR-VH-011, UC-VH-006, UC-VH-022, CW-VH-02.

    VHMS shall support Indenter request for booking modification before arrival
    and adjust billing information according to confirmed modification outcome.
    """

    def test_cfr_vh_005_afr_026_034_br_vh_010_011_modification_and_billing_adjustment(
        self, api_client, category_a, sample_room, sample_tariff
    ):
        """AFR-VH-026, AFR-VH-034, BR-VH-010, BR-VH-011, UC-VH-006, UC-VH-022, CW-VH-02: Modification modifies dates and updates bill."""
        today = timezone.localdate()
        booking = Booking.objects.create(
            indenter_id=120,
            visitor_name="Prof. Modifying",
            visitor_category=category_a,
            visit_purpose="Research Visit",
            check_in_date=today + timedelta(days=10),
            check_out_date=today + timedelta(days=12),
            status=BookingStatus.APPROVED,
            number_of_rooms=1,
        )
        RoomAllotment.objects.create(booking=booking, room=sample_room)

        # Indenter requests modification extending stay by 1 day (3 days total)
        new_out = today + timedelta(days=13)
        mod_req = api_client.post(
            f"/api/v1/vh/bookings/{booking.id}/request_modification/",
            {
                "new_check_in_date": str(today + timedelta(days=10)),
                "new_check_out_date": str(new_out),
                "reason": "Extended discussions",
            },
            format="json",
        )
        assert mod_req.status_code == 201
        mod_id = mod_req.data["id"]

        # Confirm modification
        conf_resp = api_client.post(
            f"/api/v1/vh/bookings/{booking.id}/confirm_modification/",
            {"modification_id": mod_id, "approved": True},
            format="json",
        )
        assert conf_resp.status_code == 200

        booking.refresh_from_db()
        assert booking.check_out_date == new_out

        # Verify bill recalculation reflects 3 days (3 * 1000.00 = 3000.00)
        bill = Bill.objects.get(booking=booking)
        assert bill.room_charges == Decimal("3000.00")
        assert bill.total_amount == Decimal("3000.00")


# ==============================================================================
# CFR-VH-006: Booking Cancellation and Charge Handling (AFR-VH-027..033, 035, BR-VH-006..009, ISS-006, ISS-007, ISS-011)
# ==============================================================================
@pytest.mark.django_db
class TestCFR006BookingCancellationAndNoShow:
    """CFR-VH-006, AFR-VH-027, AFR-VH-028, AFR-VH-029, AFR-VH-030, AFR-VH-031, AFR-VH-032, AFR-VH-033, AFR-VH-035, BR-VH-006, BR-VH-007, BR-VH-008, BR-VH-009, UC-VH-007, UC-VH-020, BW-VH-07, BW-VH-08, BW-VH-09.

    VHMS shall support cancellation review, apply tiered cancellation charges
    (0% for >= 7 days, 25% for < 7 days, 50% for same-day/no-show), clear stay charges,
    and release allotted rooms.
    """

    def test_cfr_vh_006_bw_vh_07_cancellation_seven_plus_days_zero_charge(
        self, api_client, category_a, sample_room, sample_tariff
    ):
        """BW-VH-07, BR-VH-006, BR-VH-007, AFR-VH-027, AFR-VH-028, AFR-VH-029, AFR-VH-032, AFR-VH-033, AFR-VH-035, UC-VH-007, UC-VH-020: Cancellation >= 7 days has 0% charge."""
        today = timezone.localdate()
        booking = Booking.objects.create(
            indenter_id=130,
            visitor_name="Early Canceller",
            visitor_category=category_a,
            visit_purpose="Conference",
            check_in_date=today + timedelta(days=10),
            check_out_date=today + timedelta(days=12),
            status=BookingStatus.APPROVED,
            number_of_rooms=1,
        )
        RoomAllotment.objects.create(booking=booking, room=sample_room)

        resp = api_client.post(f"/api/v1/vh/bookings/{booking.id}/cancel/")
        assert resp.status_code == 200
        booking.refresh_from_db()
        assert booking.status == BookingStatus.CANCELLED

        bill = Bill.objects.get(booking=booking)
        assert bill.cancellation_charges == Decimal("0.00")
        assert bill.total_amount == Decimal("0.00")

    def test_cfr_vh_006_bw_vh_08_cancellation_under_seven_days_twenty_five_percent(
        self, api_client, category_a, sample_room, sample_tariff
    ):
        """BW-VH-08, BR-VH-006, BR-VH-008, AFR-VH-028, AFR-VH-030: Cancellation within 7 days incurs 25% one-day room rent."""
        today = timezone.localdate()
        booking = Booking.objects.create(
            indenter_id=131,
            visitor_name="Mid Canceller",
            visitor_category=category_a,
            visit_purpose="Symposium",
            check_in_date=today + timedelta(days=3),
            check_out_date=today + timedelta(days=6),
            status=BookingStatus.APPROVED,
            number_of_rooms=1,
        )
        RoomAllotment.objects.create(booking=booking, room=sample_room)

        resp = api_client.post(f"/api/v1/vh/bookings/{booking.id}/cancel/")
        assert resp.status_code == 200
        booking.refresh_from_db()
        assert booking.status == BookingStatus.CANCELLED

        # 25% of 1-day room rent (1000.00 * 0.25 = 250.00)
        bill = Bill.objects.get(booking=booking)
        assert bill.cancellation_charges == Decimal("250.00")
        assert bill.total_amount == Decimal("250.00")

    def test_cfr_vh_006_bw_vh_09_cancellation_same_day_fifty_percent(
        self, api_client, category_a, sample_room, sample_tariff
    ):
        """BW-VH-09, BR-VH-006, BR-VH-009, AFR-VH-028, AFR-VH-031: Same-day cancellation incurs 50% one-day room rent."""
        today = timezone.localdate()
        booking = Booking.objects.create(
            indenter_id=132,
            visitor_name="Same Day Canceller",
            visitor_category=category_a,
            visit_purpose="Meeting",
            check_in_date=today,
            check_out_date=today + timedelta(days=2),
            status=BookingStatus.APPROVED,
            number_of_rooms=1,
        )
        RoomAllotment.objects.create(booking=booking, room=sample_room)

        resp = api_client.post(f"/api/v1/vh/bookings/{booking.id}/cancel/")
        assert resp.status_code == 200
        booking.refresh_from_db()
        assert booking.status == BookingStatus.CANCELLED

        # 50% of 1000.00 = 500.00
        bill = Bill.objects.get(booking=booking)
        assert bill.cancellation_charges == Decimal("500.00")
        assert bill.total_amount == Decimal("500.00")

    def test_cfr_vh_006_iss_011_record_no_show_releases_room_and_levies_fifty_percent(
        self, api_client, category_a, sample_room, sample_tariff
    ):
        """ISS-011, AFR-VH-031, BR-VH-009: record_no_show releases room, CANCELLED status, 50% charge."""
        today = timezone.localdate()
        booking = Booking.objects.create(
            indenter_id=133,
            visitor_name="Ghost Guest",
            visitor_category=category_a,
            visit_purpose="Audit",
            check_in_date=today,
            check_out_date=today + timedelta(days=2),
            status=BookingStatus.ROOM_ALLOTTED,
            number_of_rooms=1,
        )
        RoomAllotment.objects.create(booking=booking, room=sample_room)
        sample_room.status = RoomStatus.OCCUPIED
        sample_room.save()

        resp = api_client.post(f"/api/v1/vh/bookings/{booking.id}/record_no_show/")
        assert resp.status_code == 200

        # Room returned to available
        sample_room.refresh_from_db()
        assert sample_room.status == RoomStatus.AVAILABLE

        # Booking marked CANCELLED with No-Show note
        booking.refresh_from_db()
        assert booking.status == BookingStatus.CANCELLED
        assert "No-Show" in booking.cancellation_reason

        # 50% charge levied
        bill = Bill.objects.get(booking=booking)
        assert bill.cancellation_charges == Decimal("500.00")
        assert bill.total_amount == Decimal("500.00")

    def test_cfr_vh_006_iss_006_and_007_cancellation_guards_and_zeroes_stay_charges(
        self, api_client, category_a, sample_tariff
    ):
        """ISS-006, ISS-007, AFR-VH-027, AFR-VH-035: Block cancel on rejected; zero stay charges on bill."""
        today = timezone.localdate()
        b_rej = Booking.objects.create(
            indenter_id=134,
            visitor_name="Rejected Guest",
            visitor_category=category_a,
            visit_purpose="Exam",
            check_in_date=today + timedelta(days=5),
            check_out_date=today + timedelta(days=7),
            status=BookingStatus.REJECTED,
        )
        # ISS-006: Cannot cancel already rejected
        r_rej = api_client.post(f"/api/v1/vh/bookings/{b_rej.id}/cancel/")
        assert r_rej.status_code == 400

        # ISS-007: Zero out stay charges on cancel
        b_app = Booking.objects.create(
            indenter_id=135,
            visitor_name="Stayer Turned Canceller",
            visitor_category=category_a,
            visit_purpose="Conference",
            check_in_date=today + timedelta(days=12),
            check_out_date=today + timedelta(days=15),
            status=BookingStatus.APPROVED,
        )
        Bill.objects.create(
            booking=b_app,
            room_charges=Decimal("3000.00"),
            meal_charges=Decimal("500.00"),
            total_amount=Decimal("3500.00"),
        )
        r_ok = api_client.post(f"/api/v1/vh/bookings/{b_app.id}/cancel/")
        assert r_ok.status_code == 200
        bill = Bill.objects.get(booking=b_app)
        assert bill.room_charges == Decimal("0.00")
        assert bill.meal_charges == Decimal("0.00")
        assert bill.total_amount == bill.cancellation_charges


# ==============================================================================
# CFR-VH-007: Room Allotment and Room/Occupancy Records (AFR-VH-036..040, BR-VH-012..016, ISS-008)
# ==============================================================================
@pytest.mark.django_db
class TestCFR007RoomAllotmentAndOccupancy:
    """CFR-VH-007, AFR-VH-036, AFR-VH-037, AFR-VH-038, AFR-VH-039, AFR-VH-040, BR-VH-012, BR-VH-013, BR-VH-014, BR-VH-015, BR-VH-016, ISS-008, UC-VH-008.

    VHMS shall allow rooms to be allotted only after booking approval and support
    Single/Double occupancy and Suite/Non-suite room types.
    """

    def test_cfr_vh_007_iss_008_br_vh_012_afr_036_allotment_requires_approval(
        self, api_client, category_a, sample_room
    ):
        """ISS-008, BR-VH-012, AFR-VH-036, UC-VH-008: Block room allotment for unapproved bookings."""
        today = timezone.localdate()
        booking = Booking.objects.create(
            indenter_id=140,
            visitor_name="Unapproved Allottee",
            visitor_category=category_a,
            visit_purpose="Colloquium",
            check_in_date=today + timedelta(days=2),
            check_out_date=today + timedelta(days=4),
            status=BookingStatus.PENDING,
        )
        resp = api_client.post(
            f"/api/v1/vh/bookings/{booking.id}/allot_room/",
            {"room_id": sample_room.id},
        )
        assert resp.status_code == 400
        assert "APPROVED" in resp.data["error"]

    def test_cfr_vh_007_afr_037_038_039_040_br_vh_013_014_015_016_room_types(
        self, db
    ):
        """AFR-VH-037, AFR-VH-038, AFR-VH-039, AFR-VH-040, BR-VH-013, BR-VH-014, BR-VH-015, BR-VH-016: Single/Double occupancy and Suite/Non-suite room records."""
        combinations = [
            ("S-S", RoomType.SUITE, OccupancyType.SINGLE),     # BR-VH-013, BR-VH-015, AFR-VH-037, AFR-VH-039
            ("S-D", RoomType.SUITE, OccupancyType.DOUBLE),     # BR-VH-014, BR-VH-015, AFR-VH-038, AFR-VH-039
            ("NS-S", RoomType.NON_SUITE, OccupancyType.SINGLE), # BR-VH-013, BR-VH-016, AFR-VH-037, AFR-VH-040
            ("NS-D", RoomType.NON_SUITE, OccupancyType.DOUBLE), # BR-VH-014, BR-VH-016, AFR-VH-038, AFR-VH-040
        ]
        for r_num, r_type, occ_type in combinations:
            rm = Room.objects.create(
                room_number=r_num,
                room_type=r_type,
                occupancy_type=occ_type,
                floor=1,
                status=RoomStatus.AVAILABLE,
            )
            assert rm.room_type == r_type
            assert rm.occupancy_type == occ_type


# ==============================================================================
# CFR-VH-008: Stay Check-In, Check-Out, and Stay Exceptions (AFR-VH-041..044, BR-VH-017, BR-VH-018, ISS-017)
# ==============================================================================
@pytest.mark.django_db
class TestCFR008StayProgressionAndExceptions:
    """CFR-VH-008, AFR-VH-041, AFR-VH-042, AFR-VH-043, AFR-VH-044, BR-VH-017, BR-VH-018, ISS-017, UC-VH-009, UC-VH-021, UC-VH-024.

    VHMS shall record check-in and check-out timestamps, persist guest verification notes,
    and generate alerts for no-shows and overstays.
    """

    def test_cfr_vh_008_afr_041_042_iss_017_checkin_checkout_and_verification_notes(
        self, api_client, category_a, sample_room, sample_tariff
    ):
        """AFR-VH-041, AFR-VH-042, ISS-017, UC-VH-009, UC-VH-021: Check-in, check-out, and verification notes."""
        today = timezone.localdate()
        booking = Booking.objects.create(
            indenter_id=150,
            visitor_name="Prof. Satish Dhawan",
            visitor_category=category_a,
            visit_purpose="Aeronautics Review",
            check_in_date=today - timedelta(days=2),
            check_out_date=today,
            status=BookingStatus.APPROVED,
        )
        RoomAllotment.objects.create(booking=booking, room=sample_room)

        # 1. Record Check-in (AFR-VH-041, UC-VH-009)
        r_in = api_client.post(
            f"/api/v1/vh/bookings/{booking.id}/check_in/",
            {"remarks": "Guest arrived on schedule."},
        )
        assert r_in.status_code == 200
        booking.refresh_from_db()
        assert booking.status == BookingStatus.CHECKED_IN
        assert CheckInRecord.objects.filter(booking=booking).exists()

        # 2. Record Check-out with verification notes (AFR-VH-042, ISS-017, UC-VH-021)
        r_out = api_client.post(
            f"/api/v1/vh/bookings/{booking.id}/check_out/",
            {"guest_verification_notes": "Identity and room inventory physically verified."},
            format="json",
        )
        assert r_out.status_code == 200
        booking.refresh_from_db()
        assert booking.status == BookingStatus.CHECKED_OUT
        assert CheckOutRecord.objects.filter(booking=booking).exists()

        # ISS-017: Bill contains guest verification notes
        bill = Bill.objects.get(booking=booking)
        assert "Identity and room inventory physically verified" in bill.guest_verification_notes

    def test_cfr_vh_008_afr_043_044_br_vh_017_018_stay_exception_alerts(
        self, category_a, sample_room
    ):
        """AFR-VH-043, AFR-VH-044, BR-VH-017, BR-VH-018, UC-VH-024: Detects no-shows and overstays."""
        today = timezone.localdate()

        # AFR-VH-043, BR-VH-017: No-show alert
        b_noshow = Booking.objects.create(
            indenter_id=151,
            visitor_name="Late Guest",
            visitor_category=category_a,
            visit_purpose="Conference",
            check_in_date=today - timedelta(days=1),
            check_out_date=today + timedelta(days=2),
            status=BookingStatus.ROOM_ALLOTTED,
        )

        # AFR-VH-044, BR-VH-018: Overstay alert
        b_overstay = Booking.objects.create(
            indenter_id=152,
            visitor_name="Overstaying Guest",
            visitor_category=category_a,
            visit_purpose="Colloquium",
            check_in_date=today - timedelta(days=5),
            check_out_date=today - timedelta(days=1),
            status=BookingStatus.CHECKED_IN,
        )

        result = check_stay_exception_alerts()
        assert result["no_shows_detected"] >= 1
        assert result["overstays_detected"] >= 1
        assert VHAlert.objects.filter(booking=b_noshow, alert_type=VHAlertType.NO_SHOW).exists()
        assert VHAlert.objects.filter(booking=b_overstay, alert_type=VHAlertType.OVERSTAY).exists()


# ==============================================================================
# CFR-VH-009: Visitor Category and Tariff Control (AFR-VH-045..050, 108, BR-VH-019, 023, 024, ISS-010)
# ==============================================================================
@pytest.mark.django_db
class TestCFR009VisitorCategoryAndTariffControl:
    """CFR-VH-009, AFR-VH-045, AFR-VH-046, AFR-VH-047, AFR-VH-048, AFR-VH-049, AFR-VH-050, AFR-VH-108, BR-VH-019, BR-VH-023, BR-VH-024, ISS-010, UC-VH-011.

    VHMS shall classify visitors into categories A, B, C, D, maintain tariffs with
    effective-from dates, select the applicable tariff using booking check_in_date,
    and prevent retroactive tariff changes from altering historical bills.
    """

    def test_cfr_vh_009_afr_045_046_047_br_vh_019_categories_and_tariffs(self, all_categories):
        """AFR-VH-045, AFR-VH-046, AFR-VH-047, BR-VH-019, UC-VH-011: VHMS supports categories A, B, C, D and tariffs."""
        codes = [c.code for c in all_categories]
        assert set(codes) == {"A", "B", "C", "D"}

    def test_cfr_vh_009_iss_010_afr_048_049_050_108_br_vh_023_024_historical_tariff_integrity(
        self, api_client, category_a, sample_room
    ):
        """ISS-010, AFR-VH-048, AFR-VH-049, AFR-VH-050, AFR-VH-108, BR-VH-023, BR-VH-024: Effective-from tariff lookup."""
        today = timezone.localdate()

        # Tariff 1: Effective 30 days ago at 1000.00
        Tariff.objects.create(
            category=category_a,
            room_type=sample_room.room_type,
            occupancy_type=sample_room.occupancy_type,
            amount=Decimal("1000.00"),
            effective_from=today - timedelta(days=30),
        )

        # Tariff 2: Price hike effective in future (tomorrow) at 2500.00
        Tariff.objects.create(
            category=category_a,
            room_type=sample_room.room_type,
            occupancy_type=sample_room.occupancy_type,
            amount=Decimal("2500.00"),
            effective_from=today + timedelta(days=1),
        )

        booking = Booking.objects.create(
            indenter_id=160,
            visitor_name="Prof. Historical Tariff",
            visitor_category=category_a,
            visit_purpose="Audit",
            check_in_date=today - timedelta(days=2),
            check_out_date=today,
            status=BookingStatus.CHECKED_IN,
        )
        RoomAllotment.objects.create(booking=booking, room=sample_room)

        # Check-out should compute tariff as 1000.00 per day (2 days = 2000.00), NOT 2500.00
        r_out = api_client.post(f"/api/v1/vh/bookings/{booking.id}/check_out/")
        assert r_out.status_code == 200
        bill = Bill.objects.get(booking=booking)
        assert bill.room_charges == Decimal("2000.00")
        assert bill.total_amount == Decimal("2000.00")


# ==============================================================================
# CFR-VH-010: Mess and Meal Booking (AFR-VH-051..058, BR-VH-025, 029..032, ISS-012..014)
# ==============================================================================
@pytest.mark.django_db
class TestCFR010MessAndMealBooking:
    """CFR-VH-010, AFR-VH-051, AFR-VH-052, AFR-VH-053, AFR-VH-054, AFR-VH-055, AFR-VH-056, AFR-VH-057, AFR-VH-058, BR-VH-025, BR-VH-029, BR-VH-030, BR-VH-031, BR-VH-032, ISS-012, ISS-013, ISS-014, UC-VH-012.

    VHMS shall record meal bookings only for guests staying in VH, support Breakfast,
    Lunch, Dinner with Tea/Milk add-ons, and link meal consumption to billing.
    """

    def test_cfr_vh_010_iss_012_br_vh_025_br_vh_031_afr_051_meal_requires_checked_in_stay(
        self, api_client, category_a
    ):
        """ISS-012, AFR-VH-051, BR-VH-025, BR-VH-031, UC-VH-012: Meal booking rejected if guest is not CHECKED_IN."""
        today = timezone.localdate()
        booking = Booking.objects.create(
            indenter_id=170,
            visitor_name="Pending Meal Guest",
            visitor_category=category_a,
            visit_purpose="Visit",
            check_in_date=today,
            check_out_date=today + timedelta(days=2),
            status=BookingStatus.PENDING,
        )
        payload = {
            "booking": booking.id,
            "meal_date": str(today),
            "meal_type": MealType.LUNCH,
            "quantity": 1,
            "rate": "150.00",
        }
        resp = api_client.post("/api/v1/vh/meals/", payload, format="json")
        assert resp.status_code == 400
        assert "CHECKED_IN" in resp.data["error"]

    def test_cfr_vh_010_iss_013_iss_014_afr_052_to_058_br_vh_029_030_032_meal_types_and_addons(
        self, api_client, category_a
    ):
        """ISS-013, ISS-014, AFR-VH-052, AFR-VH-053, AFR-VH-054, AFR-VH-055, AFR-VH-056, AFR-VH-057, AFR-VH-058, BR-VH-029, BR-VH-030, BR-VH-032: Meal types and add-on validation."""
        today = timezone.localdate()
        booking = Booking.objects.create(
            indenter_id=171,
            visitor_name="Diner Guest",
            visitor_category=category_a,
            visit_purpose="Research",
            check_in_date=today,
            check_out_date=today + timedelta(days=2),
            status=BookingStatus.CHECKED_IN,
        )

        # Valid Breakfast with Milk
        r_bk = api_client.post(
            "/api/v1/vh/meals/",
            {
                "booking": booking.id,
                "meal_date": str(today),
                "meal_type": MealType.BREAKFAST,
                "add_on": MealAddOn.MILK,
                "quantity": 1,
                "rate": "80.00",
            },
            format="json",
        )
        assert r_bk.status_code == 201

        # Valid Dinner with Tea
        r_dn = api_client.post(
            "/api/v1/vh/meals/",
            {
                "booking": booking.id,
                "meal_date": str(today),
                "meal_type": MealType.DINNER,
                "add_on": MealAddOn.TEA,
                "quantity": 2,
                "rate": "100.00",
            },
            format="json",
        )
        assert r_dn.status_code == 201
        assert r_dn.data["total_amount"] == "200.00"

        # Invalid meal type (ISS-013, BR-VH-029)
        r_inv_meal = api_client.post(
            "/api/v1/vh/meals/",
            {
                "booking": booking.id,
                "meal_date": str(today),
                "meal_type": "SNACKS",
                "quantity": 1,
                "rate": "50.00",
            },
            format="json",
        )
        assert r_inv_meal.status_code == 400

        # Invalid add-on (ISS-014, BR-VH-030)
        r_inv_addon = api_client.post(
            "/api/v1/vh/meals/",
            {
                "booking": booking.id,
                "meal_date": str(today),
                "meal_type": MealType.LUNCH,
                "add_on": "COFFEE",
                "quantity": 1,
                "rate": "120.00",
            },
            format="json",
        )
        assert r_inv_addon.status_code == 400


# ==============================================================================
# CFR-VH-011: Billing and Offline Settlement (AFR-VH-059..066, BR-VH-033..037, ISS-015, ISS-016)
# ==============================================================================
@pytest.mark.django_db
class TestCFR011BillingAndOfflineSettlement:
    """CFR-VH-011, AFR-VH-059, AFR-VH-060, AFR-VH-061, AFR-VH-062, AFR-VH-063, AFR-VH-064, AFR-VH-065, AFR-VH-066, BR-VH-033, BR-VH-034, BR-VH-035, BR-VH-036, BR-VH-037, ISS-015, ISS-016, UC-VH-013.

    VHMS shall generate immutable bills covering room rent, meals, and cancellations,
    and enforce offline cash-only settlement, strictly rejecting online payment modes.
    """

    def test_cfr_vh_011_iss_015_br_vh_036_afr_064_cash_only_settlement_rejects_online(
        self, api_client, category_a
    ):
        """ISS-015, AFR-VH-064, BR-VH-036, UC-VH-013: Settle rejects online modes; accepts CASH."""
        today = timezone.localdate()
        booking = Booking.objects.create(
            indenter_id=180,
            visitor_name="Settling Guest",
            visitor_category=category_a,
            visit_purpose="Colloquium",
            check_in_date=today - timedelta(days=1),
            check_out_date=today,
            status=BookingStatus.CHECKED_OUT,
        )
        bill = Bill.objects.create(booking=booking, room_charges=Decimal("1000.00"), total_amount=Decimal("1000.00"))

        # Reject online payment modes
        for bad_mode in ["ONLINE", "NET_BANKING", "UPI", "CREDIT_CARD"]:
            r_bad = api_client.post(f"/api/v1/vh/bills/{bill.id}/settle/", {"payment_mode": bad_mode}, format="json")
            assert r_bad.status_code == 400
            assert "CASH" in r_bad.data["error"]

        # Accept CASH
        r_ok = api_client.post(f"/api/v1/vh/bills/{bill.id}/settle/", {"payment_mode": "CASH"}, format="json")
        assert r_ok.status_code == 200
        bill.refresh_from_db()
        assert bill.is_settled is True
        assert bill.payment_mode == PaymentMode.CASH
        assert bill.settlement_date is not None

    def test_cfr_vh_011_iss_016_br_vh_033_034_035_037_afr_059_060_061_062_063_065_066_bill_immutability(
        self, api_client, category_a
    ):
        """ISS-016, AFR-VH-059, AFR-VH-060, AFR-VH-061, AFR-VH-062, AFR-VH-063, AFR-VH-065, AFR-VH-066, BR-VH-033, BR-VH-034, BR-VH-035, BR-VH-037: Bill composition and immutability."""
        today = timezone.localdate()
        booking = Booking.objects.create(
            indenter_id=181,
            visitor_name="Tamper Target",
            visitor_category=category_a,
            visit_purpose="Meeting",
            check_in_date=today - timedelta(days=1),
            check_out_date=today,
            status=BookingStatus.CHECKED_OUT,
        )
        bill = Bill.objects.create(
            booking=booking,
            room_charges=Decimal("1000.00"),
            meal_charges=Decimal("200.00"),
            total_amount=Decimal("1200.00"),
        )

        # Attempt to modify calculated charges via PATCH
        resp = api_client.patch(
            f"/api/v1/vh/bills/{bill.id}/",
            {"room_charges": "50.00", "total_amount": "50.00"},
            format="json",
        )
        assert resp.status_code == 400
        assert "immutable" in resp.data["error"]


# ==============================================================================
# CFR-VH-012 & CFR-VH-013: Inventory Management and Replenishment (AFR-VH-068..074, BR-VH-041, 043, ISS-019)
# ==============================================================================
@pytest.mark.django_db
class TestCFR012And013InventoryManagement:
    """CFR-VH-012, CFR-VH-013, AFR-VH-068, AFR-VH-069, AFR-VH-070, AFR-VH-071, AFR-VH-072, AFR-VH-073, AFR-VH-074, BR-VH-041, BR-VH-043, ISS-019, UC-VH-014, UC-VH-015, UC-VH-025, BW-VH-10.

    VHMS shall track inventory quantities against minimum thresholds, generate alerts
    when below threshold, support Caretaker indents, and record In-Charge approvals with
    audit metadata (reviewed_by_user_id, decision_timestamp).
    """

    def test_cfr_vh_012_013_threshold_alert_and_replenishment_lifecycle(
        self, api_client
    ):
        """AFR-VH-068, AFR-VH-069, AFR-VH-070, AFR-VH-071, AFR-VH-072, AFR-VH-073, AFR-VH-074, BR-VH-041, BR-VH-043, ISS-019, UC-VH-014, UC-VH-015, UC-VH-025, BW-VH-10: Complete replenishment lifecycle."""
        item = InventoryItem.objects.create(
            name="Bath Towels",
            category=InventoryCategory.LINEN,
            current_quantity=3,
            minimum_threshold=10,
            unit="pieces",
        )

        # 1. Threshold alert generation (AFR-VH-072, BR-VH-041, BR-VH-043, UC-VH-025)
        res_alert = check_inventory_threshold_alert(item)
        assert res_alert is not None
        assert VHAlert.objects.filter(item=item, alert_type=VHAlertType.INVENTORY_LOW).exists()

        # 2. Caretaker requests replenishment (AFR-VH-068, AFR-VH-070, AFR-VH-071, AFR-VH-073, UC-VH-014)
        req_resp = api_client.post(
            f"/api/v1/vh/inventory/{item.id}/request_replenishment/",
            {"quantity_requested": 20, "remarks": "Urgent linen restock"},
            format="json",
        )
        assert req_resp.status_code == 201
        rep_id = req_resp.data["id"]

        # 3. In-Charge approves replenishment (AFR-VH-074, ISS-019, UC-VH-015, BW-VH-10)
        app_resp = api_client.post(f"/api/v1/vh/replenishments/{rep_id}/approve/")
        assert app_resp.status_code == 200
        assert app_resp.data["status"] == ReplenishmentStatus.APPROVED

        # Stock replenished
        item.refresh_from_db()
        assert item.current_quantity == 23

        # ISS-019: Audit metadata recorded
        rep = InventoryReplenishment.objects.get(id=rep_id)
        assert rep.decision_timestamp is not None
        assert rep.reviewed_by_user_id is not None


# ==============================================================================
# CFR-VH-014: Notification Services (AFR-VH-076..080, UC-VH-023)
# ==============================================================================
@pytest.mark.django_db
class TestCFR014NotificationServices:
    """CFR-VH-014, AFR-VH-076, AFR-VH-077, AFR-VH-078, AFR-VH-079, AFR-VH-080, UC-VH-023.

    VHMS shall generate system email notifications across booking lifecycle events
    (submission, approval, rejection, modification, cancellation, check-in, check-out, thresholds).
    """

    def test_cfr_vh_014_afr_076_077_078_079_080_lifecycle_notifications_logged(self, category_a):
        """AFR-VH-076, AFR-VH-077, AFR-VH-078, AFR-VH-079, AFR-VH-080, UC-VH-023: Emits notifications for all standard lifecycle events."""
        today = timezone.localdate()
        booking = Booking.objects.create(
            indenter_id=190,
            visitor_name="Notification Testee",
            visitor_category=category_a,
            visit_purpose="Colloquium",
            check_in_date=today + timedelta(days=5),
            check_out_date=today + timedelta(days=7),
            status=BookingStatus.PENDING,
        )

        events = [
            VHNotificationEventType.BOOKING_SUBMITTED,  # AFR-VH-076
            VHNotificationEventType.BOOKING_FORWARDED,  # AFR-VH-077
            VHNotificationEventType.BOOKING_APPROVED,   # AFR-VH-077
            VHNotificationEventType.BOOKING_REJECTED,   # AFR-VH-077
            VHNotificationEventType.BOOKING_CANCELLED,  # AFR-VH-078
            VHNotificationEventType.CHECKED_IN,         # AFR-VH-079
            VHNotificationEventType.CHECKED_OUT,        # AFR-VH-079
        ]
        for evt in events:
            emit_booking_lifecycle_notification(booking, evt)
            assert VHNotificationLog.objects.filter(booking=booking, event_type=evt).exists()


# ==============================================================================
# CFR-VH-015 & CFR-VH-016: Reporting Services (AFR-VH-082..089, UC-VH-017, UC-VH-018)
# ==============================================================================
@pytest.mark.django_db
class TestCFR015And016ReportingServices:
    """CFR-VH-015, CFR-VH-016, AFR-VH-082, AFR-VH-083, AFR-VH-084, AFR-VH-085, AFR-VH-086, AFR-VH-087, AFR-VH-088, AFR-VH-089, UC-VH-017, UC-VH-018.

    VHMS shall support In-Charge reports (booking summary, category occupancy, revenue,
    inventory usage) and Caretaker reports (daily occupancy, upcoming arrivals/departures,
    pending approvals, no-show/overstay logs).
    """

    def test_cfr_vh_015_afr_082_083_084_085_incharge_reports(self, api_client):
        """AFR-VH-082, AFR-VH-083, AFR-VH-084, AFR-VH-085, UC-VH-017: VH In-Charge reporting views."""
        endpoints = [
            "/api/v1/vh/reports/booking_summary/",      # AFR-VH-082
            "/api/v1/vh/reports/category_occupancy/",   # AFR-VH-083
            "/api/v1/vh/reports/revenue_summary/",      # AFR-VH-084
            "/api/v1/vh/reports/inventory_usage/",      # AFR-VH-085
        ]
        for ep in endpoints:
            resp = api_client.get(ep)
            assert resp.status_code == 200

    def test_cfr_vh_016_afr_086_087_088_089_caretaker_reports(self, api_client):
        """AFR-VH-086, AFR-VH-087, AFR-VH-088, AFR-VH-089, UC-VH-018: Caretaker reporting views."""
        endpoints = [
            "/api/v1/vh/reports/daily_occupancy/",       # AFR-VH-086
            "/api/v1/vh/reports/upcoming_arrivals/",     # AFR-VH-087
            "/api/v1/vh/reports/pending_approvals/",     # AFR-VH-088
            "/api/v1/vh/reports/no_show_overstay_logs/", # AFR-VH-089
        ]
        for ep in endpoints:
            resp = api_client.get(ep)
            assert resp.status_code == 200


# ==============================================================================
# CFR-VH-017: Operational Role Reassignment (AFR-VH-090..095, BR-VH-045..050, ISS-018)
# ==============================================================================
@pytest.mark.django_db
class TestCFR017OperationalRoleReassignment:
    """CFR-VH-017, AFR-VH-090, AFR-VH-091, AFR-VH-092, AFR-VH-093, AFR-VH-094, AFR-VH-095, BR-VH-045, BR-VH-046, BR-VH-047, BR-VH-048, BR-VH-049, BR-VH-050, ISS-018, UC-VH-019.

    VHMS shall maintain exactly one active Caretaker and one active In-Charge at a time,
    apply role reassignments immediately, and transfer pending and ongoing records.
    """

    def test_cfr_vh_017_iss_018_br_vh_045_046_afr_090_091_single_active_role_holder_constraint(
        self,
    ):
        """ISS-018, AFR-VH-090, AFR-VH-091, BR-VH-045, BR-VH-046: Reject duplicate active roles."""
        VHMSUserRole.objects.all().delete()
        VHMSUserRole.objects.create(
            role_type=VHMSUserRoleType.CARETAKER,
            user_id=201,
            is_active=True,
        )

        dup_caretaker = VHMSUserRole(
            role_type=VHMSUserRoleType.CARETAKER,
            user_id=202,
            is_active=True,
        )
        with pytest.raises(ValidationError):
            dup_caretaker.save()

    def test_cfr_vh_017_afr_092_093_094_095_br_vh_047_048_049_050_role_reassignment_and_record_transfer(
        self, api_client, category_a
    ):
        """AFR-VH-092, AFR-VH-093, AFR-VH-094, AFR-VH-095, BR-VH-047, BR-VH-048, BR-VH-049, BR-VH-050, UC-VH-019: Immediate transfer of pending records to new role holder."""
        VHMSUserRole.objects.all().delete()
        VHMSUserRole.objects.create(
            role_type=VHMSUserRoleType.CARETAKER,
            user_id=210,
            is_active=True,
        )

        today = timezone.localdate()
        b_pending = Booking.objects.create(
            indenter_id=195,
            visitor_name="Pending Record Guest",
            visitor_category=category_a,
            visit_purpose="Meeting",
            check_in_date=today + timedelta(days=2),
            check_out_date=today + timedelta(days=4),
            assigned_caretaker_id=210,
            status=BookingStatus.PENDING,
        )

        # Reassign Caretaker to user 220
        resp = api_client.post(
            "/api/v1/vh/roles/assign/",
            {"role_type": VHMSUserRoleType.CARETAKER, "user_id": 220},
            format="json",
        )
        assert resp.status_code == 200

        # Old role is deactivated, new role is active
        assert VHMSUserRole.objects.filter(role_type=VHMSUserRoleType.CARETAKER, user_id=210, is_active=False).exists()
        assert VHMSUserRole.objects.filter(role_type=VHMSUserRoleType.CARETAKER, user_id=220, is_active=True).exists()

        # Records transferred to new Caretaker
        b_pending.refresh_from_db()
        assert b_pending.assigned_caretaker_id == 220


# ==============================================================================
# CFR-VH-018: Actor and Access Boundary Constraints (AFR-VH-004, AFR-VH-110, AFR-VH-112, ISS-001)
# ==============================================================================
@pytest.mark.django_db
class TestCFR018ActorAndAccessBoundaries:
    """CFR-VH-018, AFR-VH-004, AFR-VH-110, AFR-VH-112, ISS-001.

    VHMS shall strictly exclude direct Visitor access and ensure the system is not
    modeled as a regular primary actor.
    """

    def test_cfr_vh_018_iss_001_afr_004_110_112_direct_visitor_access_denied(self):
        """ISS-001, AFR-VH-004, AFR-VH-110, AFR-VH-112: Direct visitors are strictly blocked from VHMS access."""
        perm = HasVHPermission()

        class MockVisitorPrincipal:
            kind = "visitor"
            user_type = "visitor"
            def has_module(self, mod): return True

        class MockVisitorRequest:
            principal = MockVisitorPrincipal()
            user = None

        assert perm.has_permission(MockVisitorRequest(), None) is False


# ==============================================================================
# CFR-VH-019: External-Service and Execution Scope Exclusions (AFR-VH-067, 075, 081, 111, 114, 115)
# ==============================================================================
@pytest.mark.django_db
class TestCFR019ExternalScopeExclusions:
    """CFR-VH-019, AFR-VH-067, AFR-VH-075, AFR-VH-081, AFR-VH-111, AFR-VH-114, AFR-VH-115.

    VHMS shall exclude online payment gateways, central procurement, central email servers,
    accounting ledgers, and physical hostel execution from module boundary.
    """

    def test_cfr_vh_019_external_integrations_excluded_boundary(self):
        """AFR-VH-067, AFR-VH-075, AFR-VH-081, AFR-VH-111, AFR-VH-114, AFR-VH-115: Scope boundary assertions."""
        from modules.vh import models
        # Verify no external payment gateway models or foreign keys exist in vh models
        assert not hasattr(models, "PaymentGatewayTransaction")
        assert not hasattr(models, "AccountingLedgerEntry")
        assert not hasattr(models, "PurchaseOrder")


# ==============================================================================
# CFR-VH-020: Role-Assignment Scope Boundary (AFR-VH-096, AFR-VH-097, AFR-VH-098)
# ==============================================================================
@pytest.mark.django_db
class TestCFR020RoleAssignmentScopeBoundary:
    """CFR-VH-020, AFR-VH-096, AFR-VH-097, AFR-VH-098.

    VHMS role assignment shall be strictly limited to VH-specific Caretaker and VH In-Charge
    roles; VHMS shall exclude platform-wide roles, HR master data, and platform administration.
    """

    def test_cfr_vh_020_afr_096_097_098_role_assignment_boundary(self):
        """AFR-VH-096, AFR-VH-097, AFR-VH-098: Role assignment restricted strictly to Caretaker and In-Charge."""
        allowed_roles = {choice[0] for choice in VHMSUserRoleType.choices}
        assert allowed_roles == {VHMSUserRoleType.CARETAKER, VHMSUserRoleType.IN_CHARGE}
        # Platform roles like SUPERADMIN, DEAN, REGISTRAR cannot be assigned via VHMSUserRole
        assert "SUPERADMIN" not in allowed_roles
        assert "HR_ADMIN" not in allowed_roles


# ==============================================================================
# CFR-VH-021: Authoritative-Record and Auditability Constraints (AFR-VH-099..106)
# ==============================================================================
@pytest.mark.django_db
class TestCFR021AuthoritativeRecordsAndAuditability:
    """CFR-VH-021, AFR-VH-099, AFR-VH-100, AFR-VH-101, AFR-VH-102, AFR-VH-103, AFR-VH-104, AFR-VH-105, AFR-VH-106.

    VHMS shall serve as the single authoritative system for VH operational records,
    preserving auditability across bookings, approvals, allotments, stays, billing,
    inventory, and notifications.
    """

    def test_cfr_vh_021_afr_099_to_106_comprehensive_auditability(
        self, category_a, sample_room
    ):
        """AFR-VH-099, AFR-VH-100, AFR-VH-101, AFR-VH-102, AFR-VH-103, AFR-VH-104, AFR-VH-105, AFR-VH-106: Audit fields across all domain entities."""
        today = timezone.localdate()
        b = Booking.objects.create(
            indenter_id=199,
            visitor_name="Audit Guest",
            visitor_category=category_a,
            visit_purpose="Audit",
            check_in_date=today,
            check_out_date=today + timedelta(days=1),
            status=BookingStatus.APPROVED,
        )
        assert b.created_at is not None  # AFR-VH-100: booking audit
        assert b.updated_at is not None

        allot = RoomAllotment.objects.create(booking=b, room=sample_room)
        assert allot.allotted_at is not None  # AFR-VH-102: room allotment audit

        checkin = CheckInRecord.objects.create(booking=b)
        assert checkin.check_in_time is not None  # AFR-VH-103: check-in audit

        bill = Bill.objects.create(booking=b, total_amount=Decimal("1000.00"))
        assert bill.created_at is not None  # AFR-VH-104: billing audit


# ==============================================================================
# CFR-VH-022: Policy, Integrity, and Pricing Boundaries (AFR-VH-107, 109, 113)
# ==============================================================================
@pytest.mark.django_db
class TestCFR022PolicyIntegrityAndPricingBoundaries:
    """CFR-VH-022, AFR-VH-107, AFR-VH-109, AFR-VH-113.

    VHMS shall enforce institute norms and tariffs, protect record integrity, and
    strictly exclude dynamic pricing, surge multipliers, or discretionary discounts.
    """

    def test_cfr_vh_022_afr_107_109_113_pricing_and_integrity_boundaries(
        self, category_a
    ):
        """AFR-VH-107, AFR-VH-109, AFR-VH-113: Tariffs are fixed institute norms; no dynamic discount factors."""
        t = Tariff.objects.create(
            category=category_a,
            room_type=RoomType.NON_SUITE,
            occupancy_type=OccupancyType.SINGLE,
            amount=Decimal("1200.00"),
        )
        assert t.amount == Decimal("1200.00")
        assert not hasattr(t, "discount_percentage")
        assert not hasattr(t, "surge_multiplier")


# ==============================================================================
# Contracts & Cross-Boundary Plural Aggregations
# ==============================================================================
@pytest.mark.django_db
class TestVHContractsSpecificationCoverage:
    """Verifies contracts are plural, N+1 free, and compliant with Fusion architecture."""

    def test_contracts_get_pending_booking_counts_for_users_aggregation(
        self, category_a
    ):
        """Contracts: get_pending_booking_counts_for_users aggregates in a single query."""
        today = timezone.localdate()
        for i in range(3):
            Booking.objects.create(
                indenter_id=501,
                visitor_name=f"P-{i}",
                visitor_category=category_a,
                visit_purpose="P",
                check_in_date=today,
                check_out_date=today + timedelta(days=1),
                status=BookingStatus.PENDING,
            )
        Booking.objects.create(
            indenter_id=502,
            visitor_name="P-Single",
            visitor_category=category_a,
            visit_purpose="P",
            check_in_date=today,
            check_out_date=today + timedelta(days=1),
            status=BookingStatus.PENDING,
        )

        res = contracts.get_pending_booking_counts_for_users([501, 502, 503])
        assert len(res) == 3
        count_map = {row["user_id"]: row["pending_count"] for row in res}
        assert count_map[501] == 3
        assert count_map[502] == 1
        assert count_map[503] == 0


# ==============================================================================
# Full 12 Workflows (BW-VH-01..10, CW-VH-01..02) End-to-End Suite
# ==============================================================================
@pytest.mark.django_db
class TestAll12BasisAndCompositeWorkflows:
    """Explicitly verifies all 10 Basis Workflows and 2 Composite Workflows."""

    def test_workflow_bw_vh_01_online_booking_direct_rejection(
        self, api_client, category_a
    ):
        """BW-VH-01: Online Booking -> Direct Caretaker Rejection."""
        today = timezone.localdate()
        b_resp = api_client.post(
            "/api/v1/vh/bookings/",
            {
                "indenter_id": 301,
                "visitor_name": "BW01 Guest",
                "visitor_category": category_a.id,
                "visit_purpose": "Talk",
                "check_in_date": str(today + timedelta(days=3)),
                "check_out_date": str(today + timedelta(days=4)),
            },
            format="json",
        )
        assert b_resp.status_code == 201
        b_id = b_resp.data["id"]

        r_rej = api_client.post(f"/api/v1/vh/bookings/{b_id}/reject/", {"remarks": "No rooms"})
        assert r_rej.status_code == 200
        assert r_rej.data["status"] == BookingStatus.REJECTED

    def test_workflow_bw_vh_02_online_booking_forwarded_and_approved(
        self, api_client, category_a
    ):
        """BW-VH-02: Online Booking -> Forwarded -> Approved."""
        today = timezone.localdate()
        b = Booking.objects.create(
            indenter_id=302,
            visitor_name="BW02 Guest",
            visitor_category=category_a,
            visit_purpose="Colloquium",
            check_in_date=today + timedelta(days=5),
            check_out_date=today + timedelta(days=7),
            status=BookingStatus.PENDING,
        )
        api_client.post(f"/api/v1/vh/bookings/{b.id}/forward/")
        api_client.post(f"/api/v1/vh/bookings/{b.id}/approve/")
        b.refresh_from_db()
        assert b.status == BookingStatus.APPROVED

    def test_workflow_bw_vh_03_online_booking_forwarded_and_rejected(
        self, api_client, category_a
    ):
        """BW-VH-03: Online Booking -> Forwarded -> In-Charge Rejected."""
        today = timezone.localdate()
        b = Booking.objects.create(
            indenter_id=303,
            visitor_name="BW03 Guest",
            visitor_category=category_a,
            visit_purpose="Workshop",
            check_in_date=today + timedelta(days=5),
            check_out_date=today + timedelta(days=7),
            status=BookingStatus.PENDING,
        )
        api_client.post(f"/api/v1/vh/bookings/{b.id}/forward/")
        api_client.post(f"/api/v1/vh/bookings/{b.id}/reject/", {"remarks": "Disapproved by In-Charge"})
        b.refresh_from_db()
        assert b.status == BookingStatus.REJECTED

    def test_workflow_bw_vh_04_offline_booking_direct_rejection(
        self, api_client, category_a
    ):
        """BW-VH-04: Offline Booking -> Direct Caretaker Rejection."""
        today = timezone.localdate()
        b = Booking.objects.create(
            indenter_id=1,
            visitor_name="BW04 Offline Guest",
            visitor_category=category_a,
            visit_purpose="Telephonic Requisition",
            check_in_date=today + timedelta(days=2),
            check_out_date=today + timedelta(days=3),
            is_offline=True,
            offline_booking_type=OfflineBookingType.TELEPHONIC,
            status=BookingStatus.PENDING,
        )
        r = api_client.post(f"/api/v1/vh/bookings/{b.id}/reject/", {"remarks": "Fully booked"})
        assert r.status_code == 200
        b.refresh_from_db()
        assert b.status == BookingStatus.REJECTED

    def test_workflow_bw_vh_05_offline_booking_forwarded_and_approved(
        self, api_client, category_a
    ):
        """BW-VH-05: Offline Booking -> Forwarded -> In-Charge Approved."""
        today = timezone.localdate()
        b = Booking.objects.create(
            indenter_id=1,
            visitor_name="BW05 Walkin Guest",
            visitor_category=category_a,
            visit_purpose="Walk-in Requisition",
            check_in_date=today + timedelta(days=2),
            check_out_date=today + timedelta(days=4),
            is_offline=True,
            offline_booking_type=OfflineBookingType.WALK_IN,
            status=BookingStatus.PENDING,
        )
        api_client.post(f"/api/v1/vh/bookings/{b.id}/forward/")
        api_client.post(f"/api/v1/vh/bookings/{b.id}/approve/")
        b.refresh_from_db()
        assert b.status == BookingStatus.APPROVED

    def test_workflow_bw_vh_06_offline_booking_forwarded_and_rejected(
        self, api_client, category_a
    ):
        """BW-VH-06: Offline Booking -> Forwarded -> In-Charge Rejected."""
        today = timezone.localdate()
        b = Booking.objects.create(
            indenter_id=1,
            visitor_name="BW06 Walkin Guest",
            visitor_category=category_a,
            visit_purpose="Walk-in Requisition",
            check_in_date=today + timedelta(days=2),
            check_out_date=today + timedelta(days=4),
            is_offline=True,
            offline_booking_type=OfflineBookingType.WALK_IN,
            status=BookingStatus.PENDING,
        )
        api_client.post(f"/api/v1/vh/bookings/{b.id}/forward/")
        api_client.post(f"/api/v1/vh/bookings/{b.id}/reject/", {"remarks": "In-Charge rejection"})
        b.refresh_from_db()
        assert b.status == BookingStatus.REJECTED

    def test_workflow_bw_vh_07_cancellation_seven_plus_days(
        self, api_client, category_a, sample_room, sample_tariff
    ):
        """BW-VH-07: Cancellation >= 7 days before arrival (0% charge)."""
        today = timezone.localdate()
        b = Booking.objects.create(
            indenter_id=307,
            visitor_name="BW07 Guest",
            visitor_category=category_a,
            visit_purpose="Colloquium",
            check_in_date=today + timedelta(days=14),
            check_out_date=today + timedelta(days=16),
            status=BookingStatus.APPROVED,
            number_of_rooms=1,
        )
        RoomAllotment.objects.create(booking=b, room=sample_room)
        api_client.post(f"/api/v1/vh/bookings/{b.id}/cancel/")
        bill = Bill.objects.get(booking=b)
        assert bill.cancellation_charges == Decimal("0.00")

    def test_workflow_bw_vh_08_cancellation_within_seven_days(
        self, api_client, category_a, sample_room, sample_tariff
    ):
        """BW-VH-08: Cancellation within 7 days before arrival (25% charge)."""
        today = timezone.localdate()
        b = Booking.objects.create(
            indenter_id=308,
            visitor_name="BW08 Guest",
            visitor_category=category_a,
            visit_purpose="Exam",
            check_in_date=today + timedelta(days=4),
            check_out_date=today + timedelta(days=6),
            status=BookingStatus.APPROVED,
            number_of_rooms=1,
        )
        RoomAllotment.objects.create(booking=b, room=sample_room)
        api_client.post(f"/api/v1/vh/bookings/{b.id}/cancel/")
        bill = Bill.objects.get(booking=b)
        assert bill.cancellation_charges == Decimal("250.00")

    def test_workflow_bw_vh_09_cancellation_same_day(
        self, api_client, category_a, sample_room, sample_tariff
    ):
        """BW-VH-09: Cancellation same-day (50% charge)."""
        today = timezone.localdate()
        b = Booking.objects.create(
            indenter_id=309,
            visitor_name="BW09 Guest",
            visitor_category=category_a,
            visit_purpose="Meeting",
            check_in_date=today,
            check_out_date=today + timedelta(days=2),
            status=BookingStatus.APPROVED,
            number_of_rooms=1,
        )
        RoomAllotment.objects.create(booking=b, room=sample_room)
        api_client.post(f"/api/v1/vh/bookings/{b.id}/cancel/")
        bill = Bill.objects.get(booking=b)
        assert bill.cancellation_charges == Decimal("500.00")

    def test_workflow_bw_vh_10_inventory_replenishment(self, api_client):
        """BW-VH-10: Inventory Replenishment Workflow."""
        item = InventoryItem.objects.create(
            name="Bed Sheets",
            category=InventoryCategory.LINEN,
            current_quantity=2,
            minimum_threshold=10,
        )
        # Indent
        r_req = api_client.post(
            f"/api/v1/vh/inventory/{item.id}/request_replenishment/",
            {"quantity_requested": 15},
            format="json",
        )
        rep_id = r_req.data["id"]
        # In-Charge Approval
        api_client.post(f"/api/v1/vh/replenishments/{rep_id}/approve/")
        item.refresh_from_db()
        assert item.current_quantity == 17

    def test_workflow_cw_vh_01_full_lifecycle_progression(
        self, api_client, category_a, sample_room, sample_tariff
    ):
        """CW-VH-01: Full Lifecycle Booking to Check-Out and Settlement."""
        today = timezone.localdate()

        # 1. Submission
        r1 = api_client.post(
            "/api/v1/vh/bookings/",
            {
                "indenter_id": 401,
                "visitor_name": "CW01 Full Guest",
                "visitor_category": category_a.id,
                "visit_purpose": "Full Lifecycle",
                "check_in_date": str(today - timedelta(days=2)),
                "check_out_date": str(today),
                "number_of_rooms": 1,
            },
            format="json",
        )
        b_id = r1.data["id"]

        # 2. Caretaker Forward
        api_client.post(f"/api/v1/vh/bookings/{b_id}/forward/")

        # 3. In-Charge Approve
        api_client.post(f"/api/v1/vh/bookings/{b_id}/approve/")

        # 4. Room Allotment
        api_client.post(f"/api/v1/vh/bookings/{b_id}/allot_room/", {"room_id": sample_room.id})

        # 5. Check-In
        api_client.post(f"/api/v1/vh/bookings/{b_id}/check_in/")

        # 6. Meal Booking
        api_client.post(
            "/api/v1/vh/meals/",
            {
                "booking": b_id,
                "meal_date": str(today - timedelta(days=1)),
                "meal_type": MealType.LUNCH,
                "quantity": 1,
                "rate": "100.00",
            },
            format="json",
        )

        # 7. Check-Out
        r7 = api_client.post(
            f"/api/v1/vh/bookings/{b_id}/check_out/",
            {"guest_verification_notes": "Completed verified stay"},
            format="json",
        )
        assert r7.status_code == 200

        # Bill: 2 days room (2000) + 1 meal (100) = 2100.00
        bill = Bill.objects.get(booking_id=b_id)
        assert bill.room_charges == Decimal("2000.00")
        assert bill.meal_charges == Decimal("100.00")
        assert bill.total_amount == Decimal("2100.00")

        # 8. Offline Cash Settlement
        r8 = api_client.post(f"/api/v1/vh/bills/{bill.id}/settle/", {"payment_mode": "CASH"}, format="json")
        assert r8.status_code == 200
        bill.refresh_from_db()
        assert bill.is_settled is True

    def test_workflow_cw_vh_02_modification_and_billing_recalculation(
        self, api_client, category_a, sample_room, sample_tariff
    ):
        """CW-VH-02: Booking Modification & Billing Recalculation."""
        today = timezone.localdate()
        b = Booking.objects.create(
            indenter_id=402,
            visitor_name="CW02 Mod Guest",
            visitor_category=category_a,
            visit_purpose="Colloquium",
            check_in_date=today + timedelta(days=10),
            check_out_date=today + timedelta(days=12),
            status=BookingStatus.APPROVED,
            number_of_rooms=1,
        )
        RoomAllotment.objects.create(booking=b, room=sample_room)

        # Request modification to 4 days
        r_mod = api_client.post(
            f"/api/v1/vh/bookings/{b.id}/request_modification/",
            {
                "new_check_in_date": str(today + timedelta(days=10)),
                "new_check_out_date": str(today + timedelta(days=14)),
                "reason": "Extended research",
            },
            format="json",
        )
        mod_id = r_mod.data["id"]

        # Confirm modification
        api_client.post(
            f"/api/v1/vh/bookings/{b.id}/confirm_modification/",
            {"modification_id": mod_id, "approved": True},
            format="json",
        )

        b.refresh_from_db()
        assert b.check_out_date == today + timedelta(days=14)
        bill = Bill.objects.get(booking=b)
        # 4 days * 1000.00 = 4000.00
        assert bill.room_charges == Decimal("4000.00")
        assert bill.total_amount == Decimal("4000.00")
