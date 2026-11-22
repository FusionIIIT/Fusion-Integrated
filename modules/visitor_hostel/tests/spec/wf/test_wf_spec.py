"""Workflow regressions exercise transitions, rollback, retries and role separation."""

import pytest

from modules.visitor_hostel.models import BookingRequest, RoomAllotment
from modules.visitor_hostel.tests.spec.conftest import endpoint

pytestmark = pytest.mark.django_db


def test_approval_requires_caretaker_then_in_charge(actor, booking, room):
    """
    Test ID: WF-01
    Source ID: BW-VH-01
    Purpose: Verify two-stage approval sequence: in-charge approval requires preceding caretaker forwarding.
    Preconditions: Pending booking.
    Action: In-charge attempts direct approval (rejected); caretaker forwards; caretaker attempts decision (denied); in-charge approves.
    Expected: Step 1 yields 400; Step 2 yields 200; Step 3 yields 403; Step 4 yields 200. Final status is approved.
    """
    assert (
        actor("vh_in_charge")
        .post(endpoint(booking, "decision"), {"decision": "approve"})
        .status_code
        == 400
    )
    assert (
        actor("vh_caretaker").post(endpoint(booking, "route"), {"action": "forward"}).status_code
        == 200
    )
    assert (
        actor("vh_caretaker")
        .post(endpoint(booking, "decision"), {"decision": "approve"})
        .status_code
        == 403
    )
    assert (
        actor("vh_in_charge")
        .post(endpoint(booking, "decision"), {"decision": "approve"})
        .status_code
        == 200
    )
    booking.refresh_from_db()
    assert booking.status == "approved"
    assert list(booking.audit_events.values_list("action", flat=True)) == ["forwarded", "approved"]


def test_forward_requires_available_capacity(actor, booking):
    """
    Test ID: WF-02
    Source ID: BW-VH-02
    Purpose: Verify caretaker cannot forward requisition if no available capacity exists for requested room type.
    Preconditions: Pending booking with 0 available rooms of type suite.
    Action: POST /api/v1/visitor-hostel/bookings/{id}/route/ with action='forward'.
    Expected: HTTP 400 Bad Request; booking remains pending.
    """
    assert (
        actor("vh_caretaker").post(endpoint(booking, "route"), {"action": "forward"}).status_code
        == 400
    )
    booking.refresh_from_db()
    assert booking.status == "pending"


def test_rejection_requires_reason(actor, booking):
    """
    Test ID: WF-03
    Source ID: BW-VH-03
    Purpose: Verify rejection transition mandates a documented rejection reason.
    Preconditions: Pending booking.
    Action: Caretaker rejects without reason (fails), then with reason (succeeds), then attempts to re-forward (fails).
    Expected: First attempt yields 400; second yields 200; subsequent forward attempt yields 400.
    """
    client = actor("vh_caretaker")
    assert client.post(endpoint(booking, "route"), {"action": "reject"}).status_code == 400
    assert (
        client.post(
            endpoint(booking, "route"), {"action": "reject", "reason": "No capacity"}
        ).status_code
        == 200
    )
    assert client.post(endpoint(booking, "route"), {"action": "forward"}).status_code == 400


@pytest.mark.parametrize("room_ids", [[], [9999], [1, 1], ["abc"], None])
def test_bad_room_allotment_is_atomic(actor, booking, room, room_ids):
    """
    Test ID: WF-04
    Source ID: BW-VH-04
    Purpose: Verify room allotment transaction is atomic and rejects malformed or duplicate room ID lists.
    Preconditions: Approved booking, available room.
    Action: POST /api/v1/visitor-hostel/bookings/{id}/allot/ with invalid room_ids lists.
    Expected: HTTP 400 Bad Request; no allotment created; room status remains available.
    """
    booking.status = "approved"
    booking.save()
    response = actor("vh_caretaker").post(
        endpoint(booking, "allot"), {"room_ids": room_ids}, format="json"
    )
    assert response.status_code == 400
    assert not RoomAllotment.objects.exists()
    room.refresh_from_db()
    assert room.status == "available"


def test_allotment_conflict_and_cancellation_release(actor, booking, room, tariff):
    """
    Test ID: WF-05
    Source ID: BW-VH-05
    Purpose: Verify conflicting room allotment is blocked and cancellation confirmation releases room for others.
    Preconditions: Approved booking 1 allotted room; approved booking 2 requests same room.
    Action: Allotment for booking 2 rejected; booking 1 indenter cancels; caretaker confirms; allotment for 2 succeeds.
    Expected: Conflict rejected with 400; cancellation confirm releases room; booking 2 successfully allotted.
    """
    booking.status = "approved"
    booking.save()
    client = actor("vh_caretaker")
    assert (
        client.post(endpoint(booking, "allot"), {"room_ids": [room.pk]}, format="json").status_code
        == 200
    )
    other = BookingRequest.objects.create(
        indenter_id=2002,
        visitor_name="Other",
        visitor_category="A",
        purpose="Visit",
        check_in_date=booking.check_in_date,
        check_out_date=booking.check_out_date,
        room_type="suite",
        status="approved",
    )
    assert (
        client.post(endpoint(other, "allot"), {"room_ids": [room.pk]}, format="json").status_code
        == 400
    )
    assert actor().post(endpoint(booking, "cancel"), {"reason": "Plans changed"}).status_code == 200
    booking.refresh_from_db()
    assert booking.status == "confirmed"
    client = actor("vh_caretaker")
    assert client.post(endpoint(booking, "cancel/confirm")).status_code == 200
    assert client.post(endpoint(booking, "cancel/confirm")).status_code == 200
    assert (
        client.post(endpoint(other, "allot"), {"room_ids": [room.pk]}, format="json").status_code
        == 200
    )


def test_pending_bookings_cannot_check_in_or_out(actor, booking):
    """
    Test ID: WF-06
    Source ID: BW-VH-06
    Purpose: Verify illegal check-in and check-out transitions from pending state are blocked.
    Preconditions: Pending booking.
    Action: Caretaker attempts check-in or check-out directly.
    Expected: HTTP 400 Bad Request for both attempts.
    """
    client = actor("vh_caretaker")
    assert client.post(endpoint(booking, "check-in")).status_code == 400
    assert client.post(endpoint(booking, "check-out")).status_code == 400


def test_partial_allotment_rolls_back(actor, booking, room):
    """
    Test ID: WF-07
    Source ID: BW-VH-07
    Purpose: Verify partial allotment failure rolls back entire allotment transaction atomically.
    Preconditions: Approved booking for 2 rooms.
    Action: Allot 1 valid room and 1 non-existent room ID.
    Expected: HTTP 400 Bad Request; 0 allotments persisted in database.
    """
    booking.status = "approved"
    booking.number_of_rooms = 2
    booking.save()
    response = actor("vh_caretaker").post(
        endpoint(booking, "allot"), {"room_ids": [room.pk, 99999]}, format="json"
    )
    assert response.status_code == 400
    assert not RoomAllotment.objects.exists()


def test_maintenance_room_cannot_be_allotted(actor, booking, room):
    """
    Test ID: WF-08
    Source ID: BW-VH-08
    Purpose: Verify rooms with maintenance status are rejected for allotment.
    Preconditions: Room marked maintenance.
    Action: Caretaker attempts to allot maintenance room.
    Expected: HTTP 400 Bad Request.
    """
    booking.status = "approved"
    booking.save()
    room.status = "maintenance"
    room.save()
    assert (
        actor("vh_caretaker")
        .post(endpoint(booking, "allot"), {"room_ids": [room.pk]}, format="json")
        .status_code
        == 400
    )

