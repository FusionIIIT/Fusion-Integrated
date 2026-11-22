# Schedule and periodic background task tests for vh module.
from datetime import date, timedelta

import pytest

from config.celery import app as celery_app
from modules.vh.models.alerts import BookingNotificationLog, StayAlert
from modules.vh.models.booking import Booking
from modules.vh.models.inventory import InventoryItem
from modules.vh.schedule import BEAT_SCHEDULE
from modules.vh.tasks import (
    check_inventory_thresholds,
    evaluate_no_shows,
    evaluate_overstays,
    send_stay_reminders,
)

pytestmark = pytest.mark.django_db


def test_beat_schedule_registered_in_celery_app():
    # Step 5.9: Proves beat entries are present in merged celery beat schedule
    configured = celery_app.conf.beat_schedule
    for name in BEAT_SCHEDULE:
        assert name in configured


def test_evaluate_no_shows_creates_alerts_idempotently():
    # BR-VH-017, UC-VH-024: Overdue arrival with no check-in raises no-show alert
    yesterday = date.today() - timedelta(days=1)
    b = Booking.objects.create(
        booking_reference="VH-NOSHOW-1",
        indenter_id=101,
        arrival_date=yesterday,
        departure_date=yesterday + timedelta(days=2),
        status="room_allotted",
        checkin_time=None,
    )

    # First run triggers alert
    count = evaluate_no_shows()
    assert count == 1
    assert StayAlert.objects.filter(booking=b, alert_type="no_show", status="active").count() == 1

    # Second run does not duplicate alert (idempotent)
    count2 = evaluate_no_shows()
    assert count2 == 0
    assert StayAlert.objects.filter(booking=b, alert_type="no_show", status="active").count() == 1


def test_evaluate_overstays_creates_alerts_idempotently():
    # BR-VH-018, UC-VH-024: Departure passed without checkout raises overstay alert
    yesterday = date.today() - timedelta(days=1)
    b = Booking.objects.create(
        booking_reference="VH-OVERSTAY-1",
        indenter_id=101,
        arrival_date=yesterday - timedelta(days=2),
        departure_date=yesterday,
        status="checked_in",
        checkout_time=None,
    )

    # First run triggers alert
    count = evaluate_overstays()
    assert count == 1
    assert StayAlert.objects.filter(booking=b, alert_type="overstay", status="active").count() == 1

    # Second run is idempotent
    count2 = evaluate_overstays()
    assert count2 == 0
    assert StayAlert.objects.filter(booking=b, alert_type="overstay", status="active").count() == 1


def test_send_stay_reminders_dispatches_notifications():
    # AFR-VH-079, UC-VH-024: Checkin and checkout notifications for today's guests
    today = date.today()
    Booking.objects.create(
        booking_reference="VH-REMIND-ARR",
        indenter_id=101,
        arrival_date=today,
        departure_date=today + timedelta(days=2),
        status="approved",
    )
    Booking.objects.create(
        booking_reference="VH-REMIND-DEP",
        indenter_id=101,
        arrival_date=today - timedelta(days=2),
        departure_date=today,
        status="checked_in",
    )

    count = send_stay_reminders()
    assert count == 2
    assert BookingNotificationLog.objects.filter(event_type="checkin_reminder").exists()
    assert BookingNotificationLog.objects.filter(event_type="checkout_reminder").exists()


def test_check_inventory_thresholds_marks_and_notifies():
    # BR-VH-041, BR-VH-043, UC-VH-025: Batch threshold detection and notification
    item = InventoryItem.objects.create(
        item_name="Kettle Filter",
        category="utensils",
        current_quantity=2,
        minimum_threshold=5,
        unit="pieces",
    )

    count = check_inventory_thresholds()
    assert count == 1
    item.refresh_from_db()
    assert item.is_threshold_alert is True
    assert BookingNotificationLog.objects.filter(event_type="inventory_threshold_alert").exists()
