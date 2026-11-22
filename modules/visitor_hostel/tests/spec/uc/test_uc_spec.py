"""Complete hostel use-case integration through the authenticated HTTP API."""

from datetime import timedelta

import pytest
from django.utils import timezone

from modules.visitor_hostel.models import Bill, BookingRequest
from modules.visitor_hostel.tests.spec.conftest import endpoint

pytestmark = pytest.mark.django_db


def test_booking_to_stay_meal_checkout_and_cash_settlement(actor, payload, room, tariff):
    """
    Test ID: UC-001-M
    Source ID: UC-VH-001 Main Flow
    Purpose: Verify end-to-end lifecycle from booking submission, forwarding, approval,
             allotment, check-in, meal booking, check-out, and offline cash settlement.
    Preconditions: Authenticated indenter, caretaker, in-charge sessions; available room and tariff.
    Action: Sequential execution through full stay lifecycle.
    Expected: Successful 200/201 across all state transitions; room returned to available;
              immutable settled bill and audit events created.
    """
    payload.update(
        check_in_date=str(timezone.localdate()),
        check_in_time="00:00",
        check_out_date=str(timezone.localdate() + timedelta(days=2)),
    )
    response = actor().post("/api/v1/visitor-hostel/bookings/", payload, format="json")
    assert response.status_code == 201, response.data

    booking = BookingRequest.objects.get(pk=response.data["id"])
    assert (
        actor("vh_caretaker").post(endpoint(booking, "route"), {"action": "forward"}).status_code
        == 200
    )
    assert (
        actor("vh_in_charge")
        .post(endpoint(booking, "decision"), {"decision": "approve"})
        .status_code
        == 200
    )
    client = actor("vh_caretaker")
    assert (
        client.post(endpoint(booking, "allot"), {"room_ids": [room.pk]}, format="json").status_code
        == 200
    )
    assert client.post(endpoint(booking, "check-in")).status_code == 200
    assert (
        client.post(
            endpoint(booking, "meals"),
            {"date": str(timezone.localdate()), "meal_type": "lunch", "quantity": 2, "rate": "60"},
            format="json",
        ).status_code
        == 201
    )
    response = client.post(endpoint(booking, "check-out"))
    assert response.status_code == 200
    assert response.data["total_amount"] == "920.00"
    assert (
        client.post(
            endpoint(booking, "settle"),
            {"receipt_number": "VH-001", "guest_verified": True},
            format="json",
        ).status_code
        == 200
    )
    bill = Bill.objects.get(booking=booking)
    assert bill.is_settled_offline and bill.settlement_date
    assert booking.audit_events.filter(action="cash_settlement", actor_id=1001).exists()
    room.refresh_from_db()
    assert room.status == "available"


def test_inventory_request_needs_in_charge_approval(actor):
    """
    Test ID: UC-008-M
    Source ID: UC-VH-008 Main Flow
    Purpose: Verify inventory replenishment request lifecycle from caretaker request to in-charge decision.
    Preconditions: Caretaker and in-charge sessions; inventory item below threshold.
    Action: Caretaker creates item, requests replenishment, attempts self-approval (fails); in-charge approves.
    Expected: Caretaker approval attempt yields 403; in-charge approval yields 200.
    """
    client = actor("vh_caretaker")
    response = client.post(
        "/api/v1/visitor-hostel/inventory/",
        {"name": "Linen", "quantity": 2, "minimum_threshold": 5},
        format="json",
    )
    assert response.status_code == 201
    assert response.data["below_threshold"]
    response = client.post(
        "/api/v1/visitor-hostel/inventory/replenish/",
        {"item": response.data["id"], "requested_quantity": 10, "status": "approved"},
        format="json",
    )
    assert response.status_code == 201
    assert response.data["status"] == "pending"
    url = f"/api/v1/visitor-hostel/inventory/replenish/{response.data['id']}/decision/"
    assert client.post(url, {"decision": "approve"}).status_code == 403
    assert actor("vh_in_charge").post(url, {"decision": "approve"}).status_code == 200

