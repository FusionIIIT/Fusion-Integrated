# Scoping and tenant/actor isolation tests for vh module.
import pytest

from modules.vh.models.booking import Booking

pytestmark = pytest.mark.django_db


def test_indenter_cannot_see_other_indenter_booking_detail(vh_client):
    # Step 5.6: Queryset narrowing yields 404, never 403, preventing resource enumeration
    client_a = vh_client(user_id=101, perms=("vh.booking.view",))
    client_b = vh_client(user_id=102, perms=("vh.booking.view",))

    booking_b = Booking.objects.create(
        booking_reference="VH-SCOPING-001",
        indenter_id=102,
        arrival_date="2026-12-01",
        departure_date="2026-12-05",
        status="pending",
    )

    # Indenter B can see their own booking
    resp_b = client_b.get(f"/api/v1/vh/bookings/{booking_b.id}/")
    assert resp_b.status_code == 200
    assert resp_b.data["id"] == booking_b.id

    # Indenter A gets 404, not 403
    resp_a = client_a.get(f"/api/v1/vh/bookings/{booking_b.id}/")
    assert resp_a.status_code == 404
    assert resp_a.data["error"]["code"] == "not_found"


def test_indenter_list_view_is_scoped_to_own_rows(vh_client):
    # List endpoint returns only bookings created by the calling indenter
    client_a = vh_client(user_id=101, perms=("vh.booking.view",))
    client_b = vh_client(user_id=102, perms=("vh.booking.view",))

    Booking.objects.create(
        booking_reference="VH-A-1",
        indenter_id=101,
        arrival_date="2026-12-01",
        departure_date="2026-12-03",
        status="pending",
    )
    Booking.objects.create(
        booking_reference="VH-A-2",
        indenter_id=101,
        arrival_date="2026-12-05",
        departure_date="2026-12-07",
        status="pending",
    )
    Booking.objects.create(
        booking_reference="VH-B-1",
        indenter_id=102,
        arrival_date="2026-12-01",
        departure_date="2026-12-03",
        status="pending",
    )

    resp_a = client_a.get("/api/v1/vh/bookings/")
    assert resp_a.status_code == 200
    refs_a = [item["booking_reference"] for item in resp_a.data]
    assert refs_a == ["VH-A-2", "VH-A-1"]

    resp_b = client_b.get("/api/v1/vh/bookings/")
    assert resp_b.status_code == 200
    refs_b = [item["booking_reference"] for item in resp_b.data]
    assert refs_b == ["VH-B-1"]


def test_caretaker_and_incharge_have_hostel_wide_visibility(vh_client):
    # Caretaker and In-Charge can see all submitted bookings across indenters
    caretaker = vh_client(user_id=201, perms=("vh.booking.view", "vh.booking.review"))
    incharge = vh_client(user_id=301, perms=("vh.booking.view", "vh.booking.approve"))

    Booking.objects.create(
        booking_reference="VH-1",
        indenter_id=101,
        arrival_date="2026-12-01",
        departure_date="2026-12-03",
        status="pending",
    )
    Booking.objects.create(
        booking_reference="VH-2",
        indenter_id=102,
        arrival_date="2026-12-05",
        departure_date="2026-12-07",
        status="pending",
    )

    resp_ct = caretaker.get("/api/v1/vh/bookings/")
    assert resp_ct.status_code == 200
    assert len(resp_ct.data) == 2

    resp_ic = incharge.get("/api/v1/vh/bookings/")
    assert resp_ic.status_code == 200
    assert len(resp_ic.data) == 2
