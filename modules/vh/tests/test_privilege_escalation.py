# Privilege escalation and RBAC gate tests for vh module.
import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.vh.models.booking import Booking
from modules.vh.registry import PERMISSIONS

pytestmark = pytest.mark.django_db


def test_permission_codes_match_registry():
    # Step 5.1: Proves all test permission strings exist in registry.PERMISSIONS
    registry_codes = {code for code, _ in PERMISSIONS}
    test_codes = {
        "vh.booking.create",
        "vh.booking.view",
        "vh.booking.update",
        "vh.booking.delete",
        "vh.booking.review",
        "vh.booking.approve",
        "vh.room.assign",
        "vh.stay.manage",
        "vh.meal.manage",
        "vh.meal.view",
        "vh.bill.create",
        "vh.bill.view",
        "vh.bill.manage",
        "vh.inventory.view",
        "vh.inventory.manage",
        "vh.inventory.approve",
        "vh.tariff.view",
        "vh.tariff.manage",
        "vh.report.view",
        "vh.report.manage",
        "vh.role.assign",
    }
    assert test_codes.issubset(registry_codes)


def test_missing_module_grant_refused_at_gate_one(stub_iam):
    # Principal has permission but NO module grant -> HTTP 403
    stub_iam(make_session(user_id=999, permissions=("vh.booking.create",), modules=()))
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token abc")
    resp = client.get("/api/v1/vh/bookings/")
    assert resp.status_code == 403
    assert resp.data["error"]["code"] == "permission_denied"


def test_indenter_cannot_review_or_route_bookings(vh_client, indenter_client):
    # Indenter has vh module and indenter perms, but lacks vh.booking.review -> 403
    booking = Booking.objects.create(
        booking_reference="VH-TEST-001",
        indenter_id=101,
        arrival_date="2026-12-01",
        departure_date="2026-12-05",
        status="pending",
    )
    resp = indenter_client.post(f"/api/v1/vh/bookings/{booking.id}/route/", {"action": "reject"})
    assert resp.status_code == 403
    assert resp.data["error"]["code"] == "permission_denied"


def test_caretaker_cannot_approve_forwarded_bookings(vh_client, caretaker_client):
    # Caretaker lacks vh.booking.approve -> 403
    booking = Booking.objects.create(
        booking_reference="VH-TEST-002",
        indenter_id=101,
        arrival_date="2026-12-01",
        departure_date="2026-12-05",
        status="forwarded",
    )
    resp = caretaker_client.post(f"/api/v1/vh/bookings/{booking.id}/decide/", {"action": "approve"})
    assert resp.status_code == 403
    assert resp.data["error"]["code"] == "permission_denied"


def test_indenter_cannot_reassign_operational_roles(indenter_client):
    # Indenter lacks vh.role.assign -> 403
    resp = indenter_client.post(
        "/api/v1/vh/roles/reassign/",
        {"role_name": "caretaker", "new_user_id": 500},
    )
    assert resp.status_code == 403


def test_indenter_cannot_settle_bills(indenter_client, db):
    # Indenter lacks vh.bill.manage -> 403
    resp = indenter_client.post("/api/v1/vh/bills/1/settle/", {"amount_paid": "500.00"})
    assert resp.status_code == 403


def test_indenter_cannot_allot_rooms(indenter_client, db):
    # Indenter lacks vh.room.assign -> 403
    resp = indenter_client.post(
        "/api/v1/vh/bookings/1/allot-rooms/", {"room_ids": [1], "occupancy_type": "single"}
    )
    assert resp.status_code == 403


def test_unauthenticated_request_is_refused(db):
    # Request without token is refused -> 401
    client = APIClient()
    resp = client.get("/api/v1/vh/bookings/")
    assert resp.status_code in {401, 403}
