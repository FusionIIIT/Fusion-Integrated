"""Unit and integration tests for VH reporting, notification, and alert services (UC-VH-017, 018, 023, 024, 025)."""
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch
import pytest
from django.utils import timezone

from modules.vh.models import (
    Bill,
    Booking,
    BookingStatus,
    InventoryCategory,
    InventoryItem,
    InventoryReplenishment,
    PaymentMode,
    ReplenishmentStatus,
    Room,
    RoomAllotment,
    RoomStatus,
    RoomType,
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


@pytest.mark.django_db
class TestInChargeReportsService:
    def test_incharge_reports_empty_db(self):
        rep = get_incharge_reports()
        assert rep["booking_summary"]["total_bookings"] == 0
        assert rep["revenue_summary"]["total_revenue"] == "0.00"
        assert rep["inventory_usage"]["total_inventory_items"] == 0

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
    def test_booking_status_counts_in_report(self, category_a, status_val):
        today = timezone.localdate()
        Booking.objects.create(
            indenter_id=1,
            visitor_name=f"Rep {status_val}",
            visitor_category=category_a,
            visit_purpose="Report",
            check_in_date=today,
            check_out_date=today + timedelta(days=1),
            status=status_val,
        )
        rep = get_incharge_reports()
        assert rep["booking_summary"]["total_bookings"] >= 1
        assert rep["booking_summary"]["by_status"].get(status_val, 0) >= 1

    @pytest.mark.parametrize("cat_code", ["A", "B", "C", "D"])
    def test_category_occupancy_aggregation(self, all_categories, cat_code):
        today = timezone.localdate()
        cat = next(c for c in all_categories if c.code == cat_code)
        Booking.objects.create(
            indenter_id=1,
            visitor_name=f"Cat {cat_code} Guest",
            visitor_category=cat,
            visit_purpose="Check",
            check_in_date=today,
            check_out_date=today + timedelta(days=2),
            number_of_rooms=2,
        )
        rep = get_incharge_reports()
        item = next(c for c in rep["category_occupancy"] if c["category_code"] == cat_code)
        assert item["bookings_count"] >= 1
        assert item["total_rooms_booked"] >= 2

    @pytest.mark.parametrize("room_chg,meal_chg,canc_chg,is_settled", [
        (Decimal("1000.00"), Decimal("200.00"), Decimal("0.00"), True),
        (Decimal("2500.00"), Decimal("0.00"), Decimal("0.00"), False),
        (Decimal("0.00"), Decimal("0.00"), Decimal("500.00"), True),
        (Decimal("5000.00"), Decimal("1000.00"), Decimal("250.00"), False),
    ])
    def test_revenue_aggregations(self, category_a, room_chg, meal_chg, canc_chg, is_settled):
        today = timezone.localdate()
        b = Booking.objects.create(
            indenter_id=1,
            visitor_name="Rev Guest",
            visitor_category=category_a,
            visit_purpose="Rev",
            check_in_date=today,
            check_out_date=today + timedelta(days=1),
        )
        tot = room_chg + meal_chg + canc_chg
        Bill.objects.create(
            booking=b,
            room_charges=room_chg,
            meal_charges=meal_chg,
            cancellation_charges=canc_chg,
            total_amount=tot,
            is_settled=is_settled,
        )
        rep = get_incharge_reports()
        assert Decimal(rep["revenue_summary"]["total_revenue"]) >= tot


@pytest.mark.django_db
class TestCaretakerReportsService:
    @pytest.mark.parametrize("arr_offset,included", [
        (0, True),   # today
        (2, True),   # 2 days from now
        (7, True),   # 7 days from now
        (8, False),  # 8 days (beyond 7-day schedule window)
        (-1, False), # yesterday
    ])
    def test_upcoming_arrivals_schedule_filter(self, category_a, arr_offset, included):
        today = timezone.localdate()
        b = Booking.objects.create(
            indenter_id=1,
            visitor_name=f"Arr Offset {arr_offset}",
            visitor_category=category_a,
            visit_purpose="Schedule",
            check_in_date=today + timedelta(days=arr_offset),
            check_out_date=today + timedelta(days=arr_offset + 2),
            status=BookingStatus.APPROVED,
        )
        rep = get_caretaker_reports()
        arrival_refs = {a["booking_reference"] for a in rep["upcoming_arrivals"]}
        if included:
            assert b.booking_reference in arrival_refs
        else:
            assert b.booking_reference not in arrival_refs

    @pytest.mark.parametrize("dep_offset,included", [
        (0, True),   # today
        (3, True),   # 3 days from now
        (7, True),   # 7 days from now
        (10, False), # 10 days (beyond 7-day window)
        (-2, False), # already past
    ])
    def test_upcoming_departures_schedule_filter(self, category_a, dep_offset, included):
        today = timezone.localdate()
        b = Booking.objects.create(
            indenter_id=1,
            visitor_name=f"Dep Offset {dep_offset}",
            visitor_category=category_a,
            visit_purpose="Schedule",
            check_in_date=today - timedelta(days=2),
            check_out_date=today + timedelta(days=dep_offset),
            status=BookingStatus.CHECKED_IN,
        )
        rep = get_caretaker_reports()
        departure_refs = {d["booking_reference"] for d in rep["upcoming_departures"]}
        if included:
            assert b.booking_reference in departure_refs
        else:
            assert b.booking_reference not in departure_refs

    @pytest.mark.parametrize("st,is_pending_review,is_pending_cancel", [
        (BookingStatus.PENDING, True, False),
        (BookingStatus.CANCELLATION_REQUESTED, False, True),
        (BookingStatus.APPROVED, False, False),
        (BookingStatus.CHECKED_IN, False, False),
    ])
    def test_pending_action_buckets(self, category_a, st, is_pending_review, is_pending_cancel):
        today = timezone.localdate()
        b = Booking.objects.create(
            indenter_id=1,
            visitor_name="Bucket Guest",
            visitor_category=category_a,
            visit_purpose="Bucket",
            check_in_date=today,
            check_out_date=today + timedelta(days=1),
            status=st,
        )
        rep = get_caretaker_reports()
        rev_count = rep["pending_actions"]["pending_review_count"]
        canc_count = rep["pending_actions"]["pending_cancellation_confirmations_count"]
        if is_pending_review:
            assert rev_count >= 1
        if is_pending_cancel:
            assert canc_count >= 1


@pytest.mark.django_db
class TestNotificationService:
    @pytest.mark.parametrize("evt", [
        VHNotificationEventType.BOOKING_SUBMITTED,
        VHNotificationEventType.BOOKING_FORWARDED,
        VHNotificationEventType.BOOKING_APPROVED,
        VHNotificationEventType.BOOKING_REJECTED,
        VHNotificationEventType.CANCELLATION_REQUESTED,
        VHNotificationEventType.BOOKING_CANCELLED,
        VHNotificationEventType.MODIFICATION_REQUESTED,
        VHNotificationEventType.MODIFICATION_CONFIRMED,
        VHNotificationEventType.INVENTORY_THRESHOLD,
    ])
    def test_emit_notification_creates_log(self, category_a, evt):
        today = timezone.localdate()
        b = Booking.objects.create(
            indenter_id=10,
            visitor_name="Notif Guest",
            visitor_email="guest@notif.com",
            visitor_category=category_a,
            visit_purpose="Notif Check",
            check_in_date=today,
            check_out_date=today + timedelta(days=1),
        )
        log = emit_booking_lifecycle_notification(booking=b, event_type=evt)
        assert log.event_type == evt
        assert log.recipient_email == "guest@notif.com"
        assert log.recipient_user_id == 10
        assert b.booking_reference in log.subject

    def test_email_send_failure_handled_silently(self, category_a):
        today = timezone.localdate()
        b = Booking.objects.create(
            indenter_id=1,
            visitor_name="Email Fail Guest",
            visitor_email="fail@test.com",
            visitor_category=category_a,
            visit_purpose="Email Fail",
            check_in_date=today,
            check_out_date=today + timedelta(days=1),
        )
        with patch("modules.vh.services.notifications.send_mail", side_effect=Exception("SMTP Down")):
            log = emit_booking_lifecycle_notification(
                booking=b,
                event_type=VHNotificationEventType.BOOKING_SUBMITTED,
            )
            assert log.id is not None  # DB transaction still committed successfully

    def test_duplicate_inventory_threshold_alert_prevented(self):
        item = InventoryItem.objects.create(
            name="Sugar Packets",
            category=InventoryCategory.CONSUMABLES,
            current_quantity=2,
            minimum_threshold=10,
        )
        alt1 = check_inventory_threshold_alert(item)
        assert alt1 is not None

        # Second call does not duplicate alert
        alt2 = check_inventory_threshold_alert(item)
        assert alt2.id == alt1.id
        assert VHAlert.objects.filter(inventory_item=item).count() == 1


@pytest.mark.django_db
class TestReportsAndAlertsEndpoints:
    def test_api_reports_incharge(self, api_client, category_a):
        resp = api_client.get("/api/v1/vh/reports/incharge/")
        assert resp.status_code == 200
        for k in ["booking_summary", "category_occupancy", "revenue_summary", "inventory_usage"]:
            assert k in resp.data

    def test_api_reports_caretaker(self, api_client, category_a):
        resp = api_client.get("/api/v1/vh/reports/caretaker/")
        assert resp.status_code == 200
        for k in ["daily_occupancy", "upcoming_arrivals", "upcoming_departures", "pending_actions", "no_show_logs"]:
            assert k in resp.data

    def test_api_alerts_scan_and_resolve(self, api_client):
        # Trigger scan
        scan_resp = api_client.post("/api/v1/vh/alerts/scan/")
        assert scan_resp.status_code == 200
        assert "no_shows_detected" in scan_resp.data

        # Create alert and resolve via API
        alert = VHAlert.objects.create(alert_type=VHAlertType.NO_SHOW, message="Resolve test")
        res_resp = api_client.post(f"/api/v1/vh/alerts/{alert.id}/resolve/")
        assert res_resp.status_code == 200
        assert res_resp.data["is_resolved"] is True

    def test_api_notifications_list_and_retrieve(self, api_client, category_a):
        today = timezone.localdate()
        b = Booking.objects.create(
            indenter_id=1,
            visitor_name="List Notif Guest",
            visitor_category=category_a,
            visit_purpose="Notif",
            check_in_date=today,
            check_out_date=today + timedelta(days=1),
        )
        emit_booking_lifecycle_notification(booking=b, event_type=VHNotificationEventType.BOOKING_SUBMITTED)

        list_resp = api_client.get("/api/v1/vh/notifications/")
        assert list_resp.status_code == 200
        items = list_resp.data.get("results", list_resp.data)
        assert len(items) >= 1
        notif_id = items[0]["id"]

        detail_resp = api_client.get(f"/api/v1/vh/notifications/{notif_id}/")
        assert detail_resp.status_code == 200
        assert detail_resp.data["event_type"] == "BOOKING_SUBMITTED"
