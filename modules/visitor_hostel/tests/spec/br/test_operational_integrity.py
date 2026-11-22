from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.utils import timezone

from modules.visitor_hostel.models import Bill, Notification, RoleAssignment
from modules.visitor_hostel.services import create_bill, queue_notification
from modules.visitor_hostel.tasks import deliver_notifications, generate_alerts
from modules.visitor_hostel.tests.spec.conftest import endpoint

pytestmark = pytest.mark.django_db


def test_generated_bill_cannot_be_repriced_or_deleted(booking, tariff):
    """
    Test ID: BR-036
    Source ID: BR-VH-036
    Purpose: Verify generated bill is immutable against modification or deletion.
    Preconditions: Created bill with total_amount 800.00.
    Action: Attempt to change total_amount, update via queryset, or delete.
    Expected: ValidationError raised; bill total remains 800.00.
    """
    bill = create_bill(booking)
    bill.total_amount = Decimal("1.00")
    with pytest.raises(ValidationError, match="immutable"):
        bill.save()
    with pytest.raises(ValidationError):
        Bill.objects.filter(pk=bill.pk).update(total_amount=1)
    with pytest.raises(ValidationError):
        bill.delete()
    assert Bill.objects.get(pk=bill.pk).total_amount == Decimal("800.00")


def test_expired_assignment_overrides_cached_iam_grant(actor, booking):
    """
    Test ID: BR-001
    Source ID: BR-VH-001
    Purpose: Verify expired role assignment revokes staff operational access immediately.
    Preconditions: Caretaker assignment expired 1 day ago.
    Action: POST /api/v1/visitor-hostel/bookings/{id}/route/.
    Expected: HTTP 403 Forbidden.
    """
    client = actor("vh_caretaker")
    RoleAssignment.objects.filter(role="vh_caretaker").update(
        starts_at=timezone.now() - timedelta(days=2), ends_at=timezone.now() - timedelta(days=1)
    )
    assert client.post(endpoint(booking, "route"), {"action": "forward"}).status_code == 403


def test_reassignment_immediately_revokes_old_operator(actor, booking):
    """
    Test ID: BR-002
    Source ID: BR-VH-002
    Purpose: Verify appointing a new operator immediately revokes access for former operator.
    Preconditions: Former caretaker 1001 reassigned to new caretaker 2002.
    Action: Former caretaker attempts forward action; new caretaker accesses booking.
    Expected: Former operator gets 403; new operator gets 200.
    """
    client = actor("vh_caretaker")
    call_command(
        "assign_hostel_role",
        "vh_caretaker",
        2002,
        email="new@example.test",
        ends_at=(timezone.now() + timedelta(days=30)).isoformat(),
        actor_id=9999,
    )
    assert client.post(endpoint(booking, "route"), {"action": "forward"}).status_code == 403
    assert RoleAssignment.objects.filter(role="vh_caretaker").count() == 1
    assert actor("vh_caretaker", user_id=2002).get(endpoint(booking)).status_code == 200


def test_notification_delivery_is_idempotent(actor, mailoutbox):
    """
    Test ID: BR-043
    Source ID: BR-VH-043
    Purpose: Verify notification queue delivery is idempotent and deduplicated.
    Preconditions: Queued notification event.
    Action: Deliver notifications twice.
    Expected: First delivery sends 1 email; second sends 0. Mail outbox contains exactly 1 email.
    """
    actor("vh_caretaker")
    event = queue_notification("inventory_threshold", key="stock-1", role="vh_caretaker")
    assert deliver_notifications() == 1
    assert deliver_notifications() == 0
    assert len(mailoutbox) == 1
    event.refresh_from_db()
    assert event.delivered_at and event.attempts == 1


def test_failed_email_remains_retryable(actor, monkeypatch):
    """
    Test ID: BR-044
    Source ID: BR-VH-044
    Purpose: Verify failed email notification remains queued with backoff for retry.
    Preconditions: Notification queued; SMTP fails with OSError.
    Action: Execute delivery task under failure condition.
    Expected: Event delivery remains None, attempt counter increments, next attempt scheduled.
    """
    actor("vh_caretaker")
    event = queue_notification("inventory_threshold", key="stock-2", role="vh_caretaker")

    def fail(*args, **kwargs):
        raise OSError("SMTP unavailable")

    monkeypatch.setattr("django.core.mail.send_mail", fail)
    assert deliver_notifications() == 0
    event.refresh_from_db()
    assert event.delivered_at is None
    assert event.attempts == 1
    assert event.next_attempt_at > timezone.now()
    assert event.last_error == "OSError"
    assert deliver_notifications() == 0
    event.refresh_from_db()
    assert event.attempts == 1


def test_no_show_alert_is_deduplicated_and_does_not_cancel_booking(booking):
    """
    Test ID: BR-009-no-show
    Source ID: BR-VH-009
    Purpose: Verify no-show alert generation creates a single notification without altering booking status.
    Preconditions: Confirmed booking past check-in date.
    Action: Run generate_alerts task twice.
    Expected: Exactly 1 notification created; booking status remains confirmed.
    """
    booking.status = "confirmed"
    booking.check_in_date = timezone.localdate() - timedelta(days=2)
    booking.check_out_date = timezone.localdate() + timedelta(days=1)
    booking.save()
    generate_alerts()
    generate_alerts()
    assert Notification.objects.filter(event="no_show_alert", booking=booking).count() == 1
    booking.refresh_from_db()
    assert booking.status == "confirmed"


def test_overstay_alert(booking):
    """
    Test ID: BR-010-overstay
    Source ID: BR-VH-010
    Purpose: Verify overstay alert triggers for guests past checkout date.
    Preconditions: Checked-in booking past checkout date.
    Action: Run generate_alerts task.
    Expected: overstay_alert notification created.
    """
    booking.status = "checked_in"
    booking.check_in_date = timezone.localdate() - timedelta(days=3)
    booking.check_out_date = timezone.localdate() - timedelta(days=1)
    booking.save()
    generate_alerts()
    assert Notification.objects.filter(event="overstay_alert", booking=booking).exists()


def test_inventory_alert_created_strictly_below_threshold(actor):
    """
    Test ID: BR-041-alert
    Source ID: BR-VH-041
    Purpose: Verify inventory alert is generated only when quantity drops strictly below threshold.
    Preconditions: Caretaker user.
    Action: Create item at threshold (5), then update to 4 (<5).
    Expected: No notification at 5; 1 notification created when reduced to 4.
    """
    client = actor("vh_caretaker")
    response = client.post(
        "/api/v1/visitor-hostel/inventory/",
        {"name": "Linen", "quantity": 5, "minimum_threshold": 5},
        format="json",
    )
    assert response.status_code == 201
    assert not Notification.objects.exists()
    response = client.patch(
        f"/api/v1/visitor-hostel/inventory/{response.data['id']}/", {"quantity": 4}, format="json"
    )
    assert response.status_code == 200
    assert Notification.objects.filter(event="inventory_threshold").count() == 1


def test_modification_requires_caretaker_review(actor, booking, room):
    """
    Test ID: BR-015
    Source ID: BR-VH-015
    Purpose: Verify booking modification requires caretaker approval and resets room allotment.
    Preconditions: Confirmed booking with allotted room.
    Action: Indenter submits modification; caretaker approves.
    Expected: Dates updated, status returned to pending, previous allotments released.
    """
    from modules.visitor_hostel.models import RoomAllotment

    booking.status = "confirmed"
    booking.save()
    RoomAllotment.objects.create(booking=booking, room=room)
    original_date = booking.check_out_date
    response = actor().post(
        endpoint(booking, "modify"),
        {"check_out_date": str(original_date + timedelta(days=1))},
        format="json",
    )
    assert response.status_code == 200
    booking.refresh_from_db()
    assert booking.check_out_date == original_date
    assert (
        actor().post(endpoint(booking, "modify/decision"), {"decision": "approve"}).status_code
        == 403
    )
    assert (
        actor("vh_caretaker")
        .post(endpoint(booking, "modify/decision"), {"decision": "approve"})
        .status_code
        == 200
    )
    booking.refresh_from_db()
    assert booking.check_out_date == original_date + timedelta(days=1)
    assert booking.status == "pending"
    assert not booking.allotments.exists()
    assert not booking.modification_request


def test_no_show_charge_uses_half_one_day_rent(actor, booking, tariff):
    """
    Test ID: BR-009-charge
    Source ID: BR-VH-009
    Purpose: Verify recording no-show assesses 50% of one-day tariff charge.
    Preconditions: Confirmed booking past check-in date.
    Action: POST /api/v1/visitor-hostel/bookings/{id}/no-show/.
    Expected: HTTP 200 with cancellation_charge = 200.00 (half of 400.00).
    """
    booking.status = "confirmed"
    booking.check_in_date = timezone.localdate() - timedelta(days=1)
    booking.save()
    response = actor("vh_caretaker").post(endpoint(booking, "no-show"))
    assert response.status_code == 200
    assert response.data["cancellation_charge"] == "200.00"


def test_reports_denied_to_indenters(actor, booking):
    """
    Test ID: BR-050
    Source ID: BR-VH-050
    Purpose: Verify operational reports endpoint is restricted to in-charge role.
    Preconditions: Indenter vs in-charge session.
    Action: GET /api/v1/visitor-hostel/reports/.
    Expected: HTTP 403 for indenter; HTTP 200 for in-charge.
    """
    assert actor().get("/api/v1/visitor-hostel/reports/").status_code == 403
    response = actor("vh_in_charge").get("/api/v1/visitor-hostel/reports/")
    assert response.status_code == 200
    assert response.data["pending_approvals"] == 1


def test_legacy_identity_never_grants_access_by_numeric_coincidence(actor, booking):
    """
    Test ID: BR-003
    Source ID: BR-VH-003
    Purpose: Verify legacy indenter IDs require explicit operator mapping before granting access.
    Preconditions: Booking with legacy_indenter_id set.
    Action: Query booking before and after map_hostel_indenter command.
    Expected: 404 before mapping; 200 only for correctly mapped new IAM user.
    """
    booking.legacy_indenter_id = 1001
    booking.indenter_id = None
    booking.save()
    assert actor().get(endpoint(booking)).status_code == 404
    call_command("map_hostel_indenter", 1001, 2002, actor_id=9999)
    assert actor().get(endpoint(booking)).status_code == 404
    assert actor(user_id=2002).get(endpoint(booking)).status_code == 200


def test_room_catalog_rejects_bad_booking_filter(actor):
    """
    Test ID: BR-018
    Source ID: BR-VH-018
    Purpose: Verify room catalog validation rejects non-numeric booking query parameter.
    Preconditions: Caretaker session.
    Action: GET /api/v1/visitor-hostel/rooms/?booking=garbage.
    Expected: HTTP 400 Bad Request.
    """
    client = actor("vh_caretaker")
    response = client.post(
        "/api/v1/visitor-hostel/rooms/",
        {"room_number": "VH-201", "room_type": "suite", "status": "occupied"},
        format="json",
    )
    assert response.status_code == 201
    assert response.data["status"] == "available"
    assert client.get("/api/v1/visitor-hostel/rooms/?booking=garbage").status_code == 400


def test_tariff_default_date_serializes_and_negative_rate_rejected(actor):
    """
    Test ID: BR-021
    Source ID: BR-VH-021
    Purpose: Verify tariff creation defaults effective_from to today and rejects negative rates.
    Preconditions: In-charge session.
    Action: POST /api/v1/visitor-hostel/tariffs/.
    Expected: HTTP 201 with default effective_from; HTTP 400 for daily_rate < 0.
    """
    client = actor("vh_in_charge")
    url = "/api/v1/visitor-hostel/tariffs/"
    data = {"category": "A", "room_type": "suite", "occupancy": "double", "daily_rate": "400"}
    response = client.post(url, data, format="json")
    assert response.status_code == 201, response.data
    assert response.data["effective_from"] == str(timezone.localdate())
    assert client.post(url, data | {"daily_rate": "-1"}, format="json").status_code == 400


def test_check_in_after_approved_departure_time_rejected(actor, booking, room):
    """
    Test ID: BR-028
    Source ID: BR-VH-028
    Purpose: Verify check-in is rejected if attempted after the approved check-out date/time.
    Preconditions: Confirmed booking with allotted room, current time past check_out_date.
    Action: POST /api/v1/visitor-hostel/bookings/{id}/check-in/.
    Expected: HTTP 400 Bad Request; booking remains confirmed.
    """
    from freezegun import freeze_time

    from modules.visitor_hostel.models import RoomAllotment

    with freeze_time("2026-11-22 12:00:00+05:30"):
        booking.status = "confirmed"
        booking.check_in_date = timezone.localdate() - timedelta(days=1)
        booking.check_out_date = timezone.localdate()
        booking.save()
        RoomAllotment.objects.create(booking=booking, room=room)
        assert actor("vh_caretaker").post(endpoint(booking, "check-in")).status_code == 400
        booking.refresh_from_db()
        assert booking.status == "confirmed"

