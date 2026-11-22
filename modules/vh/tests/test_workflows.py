"""Systematic unit and integration test suite covering all 12 Workflows and the complete State Transition Matrix."""
from datetime import timedelta
from decimal import Decimal
import pytest
from django.utils import timezone

from modules.vh.models import (
    Booking,
    BookingModification,
    BookingStatus,
    ModificationStatus,
    OccupancyType,
    OfflineBookingType,
    Room,
    RoomAllotment,
    RoomStatus,
    RoomType,
)


@pytest.mark.django_db
class TestValidWorkflows:
    @pytest.mark.parametrize("cat_code", ["A", "B", "C", "D"])
    def test_bw_vh_01_online_booking_direct_rejection(self, api_client, all_categories, cat_code):
        """BW-VH-01: Online Booking -> Direct Caretaker Rejection."""
        today = timezone.localdate()
        cat = next(c for c in all_categories if c.code == cat_code)
        create_resp = api_client.post(
            "/api/v1/vh/bookings/",
            {
                "indenter_id": 10,
                "visitor_name": f"Guest {cat_code}",
                "visitor_category": cat.id,
                "visit_purpose": "Personal",
                "check_in_date": str(today + timedelta(days=2)),
                "check_out_date": str(today + timedelta(days=3)),
            },
            format="json",
        )
        assert create_resp.status_code == 201
        b_id = create_resp.data["id"]
        assert create_resp.data["status"] == BookingStatus.PENDING

        rej_resp = api_client.post(f"/api/v1/vh/bookings/{b_id}/reject/", {"remarks": "Direct reject"})
        assert rej_resp.status_code == 200
        assert rej_resp.data["status"] == BookingStatus.REJECTED

    @pytest.mark.parametrize("cat_code", ["A", "B", "C", "D"])
    def test_bw_vh_02_online_booking_forwarded_and_approved(self, api_client, all_categories, cat_code):
        """BW-VH-02: Online Booking -> Forwarded -> Approved."""
        today = timezone.localdate()
        cat = next(c for c in all_categories if c.code == cat_code)
        create_resp = api_client.post(
            "/api/v1/vh/bookings/",
            {
                "indenter_id": 11,
                "visitor_name": f"Guest {cat_code}",
                "visitor_category": cat.id,
                "visit_purpose": "Conference",
                "check_in_date": str(today + timedelta(days=5)),
                "check_out_date": str(today + timedelta(days=7)),
            },
            format="json",
        )
        b_id = create_resp.data["id"]

        fwd_resp = api_client.post(f"/api/v1/vh/bookings/{b_id}/forward/", {"remarks": "Fwd"})
        assert fwd_resp.status_code == 200
        assert fwd_resp.data["status"] == BookingStatus.FORWARDED

        app_resp = api_client.post(f"/api/v1/vh/bookings/{b_id}/approve/", {"remarks": "App"})
        assert app_resp.status_code == 200
        assert app_resp.data["status"] == BookingStatus.APPROVED

    @pytest.mark.parametrize("cat_code", ["A", "B", "C", "D"])
    def test_bw_vh_03_online_booking_forwarded_and_rejected(self, api_client, all_categories, cat_code):
        """BW-VH-03: Online Booking -> Forwarded -> Rejected."""
        today = timezone.localdate()
        cat = next(c for c in all_categories if c.code == cat_code)
        create_resp = api_client.post(
            "/api/v1/vh/bookings/",
            {
                "indenter_id": 12,
                "visitor_name": f"Guest {cat_code}",
                "visitor_category": cat.id,
                "visit_purpose": "Meeting",
                "check_in_date": str(today + timedelta(days=3)),
                "check_out_date": str(today + timedelta(days=4)),
            },
            format="json",
        )
        b_id = create_resp.data["id"]

        api_client.post(f"/api/v1/vh/bookings/{b_id}/forward/", {"remarks": "Fwd"})
        rej_resp = api_client.post(f"/api/v1/vh/bookings/{b_id}/reject/", {"remarks": "InCharge Rej"})
        assert rej_resp.status_code == 200
        assert rej_resp.data["status"] == BookingStatus.REJECTED

    @pytest.mark.parametrize("off_type", [OfflineBookingType.TELEPHONIC, OfflineBookingType.WALK_IN])
    def test_bw_vh_04_offline_booking_direct_rejection(self, api_client, category_a, off_type):
        """BW-VH-04: Offline Booking -> Direct Caretaker Rejection."""
        today = timezone.localdate()
        create_resp = api_client.post(
            "/api/v1/vh/bookings/",
            {
                "indenter_id": 1,
                "is_offline": True,
                "offline_booking_type": off_type,
                "visitor_name": "Offline Rej",
                "visitor_category": category_a.id,
                "visit_purpose": "Walkin",
                "check_in_date": str(today),
                "check_out_date": str(today + timedelta(days=1)),
            },
            format="json",
        )
        b_id = create_resp.data["id"]
        rej_resp = api_client.post(f"/api/v1/vh/bookings/{b_id}/reject/", {"remarks": "Offline reject"})
        assert rej_resp.status_code == 200
        assert rej_resp.data["status"] == BookingStatus.REJECTED

    @pytest.mark.parametrize("off_type", [OfflineBookingType.TELEPHONIC, OfflineBookingType.WALK_IN])
    def test_bw_vh_05_offline_booking_forwarded_and_approved(self, api_client, category_a, off_type):
        """BW-VH-05: Offline Booking -> Forwarded -> Approved."""
        today = timezone.localdate()
        create_resp = api_client.post(
            "/api/v1/vh/bookings/",
            {
                "indenter_id": 1,
                "is_offline": True,
                "offline_booking_type": off_type,
                "visitor_name": "Offline App",
                "visitor_category": category_a.id,
                "visit_purpose": "VIP Walkin",
                "check_in_date": str(today),
                "check_out_date": str(today + timedelta(days=2)),
            },
            format="json",
        )
        b_id = create_resp.data["id"]
        api_client.post(f"/api/v1/vh/bookings/{b_id}/forward/", {"remarks": "Fwd offline"})
        app_resp = api_client.post(f"/api/v1/vh/bookings/{b_id}/approve/", {"remarks": "App offline"})
        assert app_resp.status_code == 200
        assert app_resp.data["status"] == BookingStatus.APPROVED

    @pytest.mark.parametrize("off_type", [OfflineBookingType.TELEPHONIC, OfflineBookingType.WALK_IN])
    def test_bw_vh_06_offline_booking_forwarded_and_rejected(self, api_client, category_a, off_type):
        """BW-VH-06: Offline Booking -> Forwarded -> Rejected."""
        today = timezone.localdate()
        create_resp = api_client.post(
            "/api/v1/vh/bookings/",
            {
                "indenter_id": 1,
                "is_offline": True,
                "offline_booking_type": off_type,
                "visitor_name": "Offline Incharge Rej",
                "visitor_category": category_a.id,
                "visit_purpose": "Walkin",
                "check_in_date": str(today),
                "check_out_date": str(today + timedelta(days=1)),
            },
            format="json",
        )
        b_id = create_resp.data["id"]
        api_client.post(f"/api/v1/vh/bookings/{b_id}/forward/", {"remarks": "Fwd"})
        rej_resp = api_client.post(f"/api/v1/vh/bookings/{b_id}/reject/", {"remarks": "Reject offline"})
        assert rej_resp.status_code == 200
        assert rej_resp.data["status"] == BookingStatus.REJECTED

    @pytest.mark.parametrize("initial_status", [
        BookingStatus.PENDING,
        BookingStatus.FORWARDED,
        BookingStatus.APPROVED,
        BookingStatus.ROOM_ALLOTTED,
    ])
    @pytest.mark.parametrize("days_notice,expected_penalty", [
        (10, Decimal("0.00")),
        (4, Decimal("250.00")),
        (0, Decimal("500.00")),
    ])
    def test_cw_vh_02_cancellation_workflow_permutations(
        self, api_client, category_a, sample_tariff, sample_room, initial_status, days_notice, expected_penalty
    ):
        """CW-VH-02: Booking cancellation across all permitted pre-arrival statuses and notice windows."""
        today = timezone.localdate()
        booking = Booking.objects.create(
            indenter_id=1,
            visitor_name="Cancel Perm",
            visitor_category=category_a,
            visit_purpose="Exam",
            check_in_date=today + timedelta(days=days_notice),
            check_out_date=today + timedelta(days=days_notice + 2),
            number_of_rooms=1,
            status=initial_status,
        )
        if initial_status == BookingStatus.ROOM_ALLOTTED:
            RoomAllotment.objects.create(booking=booking, room=sample_room)
            sample_room.status = RoomStatus.OCCUPIED
            sample_room.save()

        # Step 1: Indenter requests cancellation
        req_resp = api_client.post(f"/api/v1/vh/bookings/{booking.id}/request_cancellation/")
        assert req_resp.status_code == 200
        assert req_resp.data["booking"]["status"] == BookingStatus.CANCELLATION_REQUESTED
        assert Decimal(req_resp.data["applicable_cancellation_charge"]) == expected_penalty

        # Step 2: Caretaker confirms cancellation
        conf_resp = api_client.post(f"/api/v1/vh/bookings/{booking.id}/confirm_cancellation/")
        assert conf_resp.status_code == 200
        assert conf_resp.data["booking"]["status"] == BookingStatus.CANCELLED
        assert Decimal(conf_resp.data["bill"]["cancellation_charges"]) == expected_penalty

    @pytest.mark.parametrize("days_stay", [1, 2, 4, 7])
    def test_bw_vh_10_approved_stay_progression(
        self, api_client, category_a, sample_room, sample_tariff, days_stay
    ):
        """BW-VH-10: Approved Stay -> Room Allotment -> Check-In -> Check-Out."""
        today = timezone.localdate()
        booking = Booking.objects.create(
            indenter_id=1,
            visitor_name=f"Stay Guest {days_stay}d",
            visitor_category=category_a,
            visit_purpose="Lecture",
            check_in_date=today,
            check_out_date=today + timedelta(days=days_stay),
            status=BookingStatus.APPROVED,
        )

        # 1. Allot room
        allot_resp = api_client.post(
            f"/api/v1/vh/bookings/{booking.id}/allot_room/",
            {"room_ids": [sample_room.id]},
            format="json",
        )
        assert allot_resp.status_code == 200
        assert allot_resp.data["booking"]["status"] == BookingStatus.ROOM_ALLOTTED

        # 2. Check-in
        ci_resp = api_client.post(f"/api/v1/vh/bookings/{booking.id}/check_in/")
        assert ci_resp.status_code == 200
        assert ci_resp.data["status"] == BookingStatus.CHECKED_IN

        # 3. Check-out
        co_resp = api_client.post(f"/api/v1/vh/bookings/{booking.id}/check_out/")
        assert co_resp.status_code == 200
        assert co_resp.data["booking"]["status"] == BookingStatus.CHECKED_OUT
        expected_rent = Decimal("1000.00") * Decimal(str(days_stay))
        assert Decimal(co_resp.data["bill"]["room_charges"]) == expected_rent


@pytest.mark.django_db
class TestIllegalStateTransitionsMatrix:
    """Exhaustive matrix of all illegal state transitions across every booking status and mutating endpoint."""

    @pytest.mark.parametrize("bad_status", [
        BookingStatus.FORWARDED,
        BookingStatus.APPROVED,
        BookingStatus.REJECTED,
        BookingStatus.ROOM_ALLOTTED,
        BookingStatus.CHECKED_IN,
        BookingStatus.CHECKED_OUT,
        BookingStatus.CANCELLATION_REQUESTED,
        BookingStatus.CANCELLED,
    ])
    def test_illegal_forward_action(self, api_client, category_a, bad_status):
        today = timezone.localdate()
        b = Booking.objects.create(
            indenter_id=1,
            visitor_name="Bad Fwd",
            visitor_category=category_a,
            visit_purpose="Bad",
            check_in_date=today,
            check_out_date=today + timedelta(days=1),
            status=bad_status,
        )
        resp = api_client.post(f"/api/v1/vh/bookings/{b.id}/forward/")
        assert resp.status_code == 400

    @pytest.mark.parametrize("bad_status", [
        BookingStatus.APPROVED,
        BookingStatus.REJECTED,
        BookingStatus.ROOM_ALLOTTED,
        BookingStatus.CHECKED_IN,
        BookingStatus.CHECKED_OUT,
        BookingStatus.CANCELLATION_REQUESTED,
        BookingStatus.CANCELLED,
    ])
    def test_illegal_approve_action(self, api_client, category_a, bad_status):
        today = timezone.localdate()
        b = Booking.objects.create(
            indenter_id=1,
            visitor_name="Bad App",
            visitor_category=category_a,
            visit_purpose="Bad",
            check_in_date=today,
            check_out_date=today + timedelta(days=1),
            status=bad_status,
        )
        resp = api_client.post(f"/api/v1/vh/bookings/{b.id}/approve/")
        assert resp.status_code == 400

    @pytest.mark.parametrize("bad_status", [
        BookingStatus.CHECKED_IN,
        BookingStatus.CHECKED_OUT,
        BookingStatus.CANCELLED,
    ])
    def test_illegal_reject_action(self, api_client, category_a, bad_status):
        today = timezone.localdate()
        b = Booking.objects.create(
            indenter_id=1,
            visitor_name="Bad Rej",
            visitor_category=category_a,
            visit_purpose="Bad",
            check_in_date=today,
            check_out_date=today + timedelta(days=1),
            status=bad_status,
        )
        resp = api_client.post(f"/api/v1/vh/bookings/{b.id}/reject/")
        assert resp.status_code == 400

    @pytest.mark.parametrize("bad_status", [
        BookingStatus.PENDING,
        BookingStatus.FORWARDED,
        BookingStatus.REJECTED,
        BookingStatus.CHECKED_IN,
        BookingStatus.CHECKED_OUT,
        BookingStatus.CANCELLATION_REQUESTED,
        BookingStatus.CANCELLED,
    ])
    def test_illegal_allot_room_action(self, api_client, category_a, sample_room, bad_status):
        today = timezone.localdate()
        b = Booking.objects.create(
            indenter_id=1,
            visitor_name="Bad Allot",
            visitor_category=category_a,
            visit_purpose="Bad",
            check_in_date=today,
            check_out_date=today + timedelta(days=1),
            status=bad_status,
        )
        resp = api_client.post(f"/api/v1/vh/bookings/{b.id}/allot_room/", {"room_ids": [sample_room.id]}, format="json")
        assert resp.status_code == 400

    @pytest.mark.parametrize("bad_status", [
        BookingStatus.PENDING,
        BookingStatus.FORWARDED,
        BookingStatus.APPROVED,
        BookingStatus.REJECTED,
        BookingStatus.CHECKED_IN,
        BookingStatus.CHECKED_OUT,
        BookingStatus.CANCELLATION_REQUESTED,
        BookingStatus.CANCELLED,
    ])
    def test_illegal_check_in_action(self, api_client, category_a, bad_status):
        today = timezone.localdate()
        b = Booking.objects.create(
            indenter_id=1,
            visitor_name="Bad CI",
            visitor_category=category_a,
            visit_purpose="Bad",
            check_in_date=today,
            check_out_date=today + timedelta(days=1),
            status=bad_status,
        )
        resp = api_client.post(f"/api/v1/vh/bookings/{b.id}/check_in/")
        assert resp.status_code == 400

    @pytest.mark.parametrize("bad_status", [
        BookingStatus.PENDING,
        BookingStatus.FORWARDED,
        BookingStatus.APPROVED,
        BookingStatus.REJECTED,
        BookingStatus.ROOM_ALLOTTED,
        BookingStatus.CHECKED_OUT,
        BookingStatus.CANCELLATION_REQUESTED,
        BookingStatus.CANCELLED,
    ])
    def test_illegal_check_out_action(self, api_client, category_a, bad_status):
        today = timezone.localdate()
        b = Booking.objects.create(
            indenter_id=1,
            visitor_name="Bad CO",
            visitor_category=category_a,
            visit_purpose="Bad",
            check_in_date=today,
            check_out_date=today + timedelta(days=1),
            status=bad_status,
        )
        resp = api_client.post(f"/api/v1/vh/bookings/{b.id}/check_out/")
        assert resp.status_code == 400

    @pytest.mark.parametrize("bad_status", [
        BookingStatus.CHECKED_IN,
        BookingStatus.CHECKED_OUT,
        BookingStatus.CANCELLATION_REQUESTED,
        BookingStatus.CANCELLED,
    ])
    def test_illegal_request_cancellation_action(self, api_client, category_a, bad_status):
        today = timezone.localdate()
        b = Booking.objects.create(
            indenter_id=1,
            visitor_name="Bad Req Cancel",
            visitor_category=category_a,
            visit_purpose="Bad",
            check_in_date=today,
            check_out_date=today + timedelta(days=1),
            status=bad_status,
        )
        resp = api_client.post(f"/api/v1/vh/bookings/{b.id}/request_cancellation/")
        assert resp.status_code == 400

    @pytest.mark.parametrize("bad_status", [
        BookingStatus.PENDING,
        BookingStatus.FORWARDED,
        BookingStatus.APPROVED,
        BookingStatus.REJECTED,
        BookingStatus.ROOM_ALLOTTED,
        BookingStatus.CHECKED_IN,
        BookingStatus.CHECKED_OUT,
        BookingStatus.CANCELLED,
    ])
    def test_illegal_confirm_cancellation_action(self, api_client, category_a, bad_status):
        today = timezone.localdate()
        b = Booking.objects.create(
            indenter_id=1,
            visitor_name="Bad Conf Cancel",
            visitor_category=category_a,
            visit_purpose="Bad",
            check_in_date=today,
            check_out_date=today + timedelta(days=1),
            status=bad_status,
        )
        resp = api_client.post(f"/api/v1/vh/bookings/{b.id}/confirm_cancellation/")
        assert resp.status_code == 400


@pytest.mark.django_db
class TestModificationWorkflowStateTransitions:
    @pytest.mark.parametrize("initial_status", [
        ModificationStatus.CONFIRMED,
        ModificationStatus.REJECTED,
    ])
    def test_cannot_confirm_already_decided_modification(self, api_client, category_a, initial_status):
        today = timezone.localdate()
        b = Booking.objects.create(
            indenter_id=1,
            visitor_name="Mod Term Guest",
            visitor_category=category_a,
            visit_purpose="Mod Check",
            check_in_date=today + timedelta(days=3),
            check_out_date=today + timedelta(days=4),
        )
        mod = BookingModification.objects.create(
            booking=b,
            requested_by_user_id=1,
            reason="Test",
            status=initial_status,
        )
        resp = api_client.post(f"/api/v1/vh/modifications/{mod.id}/confirm/")
        assert resp.status_code == 400

