"""Workflow path tests generated from frozen WF_DESIGN.json."""
from __future__ import annotations

import re
from decimal import Decimal

import pytest

from modules.vh.models import (
    Bill,
    BookingStatus,
    Tariff,
)
from modules.vh.tests.spec.fr.test_helpers import case_id, load_design, make_booking, post_booking


@pytest.mark.django_db
@pytest.mark.parametrize("case", load_design("WF"), ids=case_id)
def test_workflow_path(case, api_client, category_a, sample_room):
    """Each test item retains its frozen test_id and source_id in its pytest ID."""
    source = case["source_id"]
    basis = re.search(r"BW-VH-\d{2}", source)
    if "CW-VH-01" in source:
        path_id = int(basis.group()[-2:])
        offline = path_id in (4, 5, 6)
        if offline:
            created = post_booking(api_client, category_a.id, is_offline=True, offline_booking_type="TELEPHONIC")
        else:
            created = post_booking(api_client, category_a.id)
        assert created.status_code == 201
        booking_id = created.data["id"]
        assert created.data["is_offline"] is offline
        if path_id in (1, 4):
            final = api_client.post(f"/api/v1/vh/bookings/{booking_id}/reject/", {}, format="json")
            expected = BookingStatus.REJECTED
        else:
            forwarded = api_client.post(f"/api/v1/vh/bookings/{booking_id}/forward/", {}, format="json")
            assert forwarded.status_code == 200 and forwarded.data["status"] == BookingStatus.FORWARDED
            decision = "approve" if path_id in (2, 5) else "reject"
            final = api_client.post(f"/api/v1/vh/bookings/{booking_id}/{decision}/", {}, format="json")
            expected = BookingStatus.APPROVED if decision == "approve" else BookingStatus.REJECTED
        assert final.status_code == 200 and final.data["status"] == expected
        return

    if "CW-VH-02" in source:
        path_id = int(basis.group()[-2:])
        days = {7: 7, 8: 3, 9: 0}[path_id]
        booking = make_booking(category_a, days=days)
        Tariff.objects.create(category=category_a, room_type="NON_SUITE", occupancy_type="DOUBLE", effective_from=booking.check_in_date, rate_per_day=Decimal("1000.00"))
        request = api_client.post(f"/api/v1/vh/bookings/{booking.id}/request_cancellation/", {}, format="json")
        assert request.status_code == 200
        expected_charge = {7: Decimal("0.00"), 8: Decimal("250.00"), 9: Decimal("500.00")}[path_id]
        assert Decimal(request.data["applicable_cancellation_charge"]) == expected_charge
        confirm = api_client.post(f"/api/v1/vh/bookings/{booking.id}/confirm_cancellation/", {}, format="json")
        assert confirm.status_code == 200
        assert confirm.data["booking"]["status"] == BookingStatus.CANCELLED
        assert Decimal(confirm.data["bill"]["cancellation_charges"]) == expected_charge
        return

    assert "BW-VH-10" in source
    booking = make_booking(category_a, status=BookingStatus.APPROVED, days=0, stay=1)
    allot = api_client.post(f"/api/v1/vh/bookings/{booking.id}/allot_room/", {"room_ids": [sample_room.id]}, format="json")
    assert allot.status_code == 200 and allot.data["booking"]["status"] == BookingStatus.ROOM_ALLOTTED
    checked_in = api_client.post(f"/api/v1/vh/bookings/{booking.id}/check_in/", {}, format="json")
    assert checked_in.status_code == 200 and checked_in.data["status"] == BookingStatus.CHECKED_IN
    checked_out = api_client.post(f"/api/v1/vh/bookings/{booking.id}/check_out/", {}, format="json")
    assert checked_out.status_code == 200 and checked_out.data["booking"]["status"] == BookingStatus.CHECKED_OUT
    assert Bill.objects.filter(booking=booking).exists()
