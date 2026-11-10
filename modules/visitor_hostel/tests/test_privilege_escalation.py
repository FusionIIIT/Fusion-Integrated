"""Who may not do what. Each refusal here is paired with the role it must not
lock out, elsewhere in the suite or right beside it."""
import pytest

from modules.visitor_hostel.models import Booking, InventoryItem, Room
from modules.visitor_hostel.tests.conftest import (
    BASE,
    CARETAKER,
    CARETAKER_ID,
    INCHARGE,
    INCHARGE_ID,
    INDENTER,
    INDENTER_ID,
    make_booking,
    requisition,
)

pytestmark = [pytest.mark.django_db, pytest.mark.urls("modules.visitor_hostel.tests.urls")]


def _status(booking):
    return Booking.objects.get(pk=booking.pk).status


def test_an_indenter_cannot_route_decide_or_allot_their_own_booking(act, world):
    booking = make_booking(status="pending")
    indenter = act(INDENTER_ID, INDENTER)
    assert indenter.post(f"{BASE}/bookings/{booking.pk}/review",
                         {"outcome": "forward"}, format="json").status_code == 403
    Booking.objects.filter(pk=booking.pk).update(status="forwarded")
    assert indenter.post(f"{BASE}/bookings/{booking.pk}/decision",
                         {"outcome": "approve"}, format="json").status_code == 403
    assert _status(booking) == "forwarded"


def test_the_caretaker_cannot_approve(act, world):
    booking = make_booking(status="forwarded")
    r = act(CARETAKER_ID, CARETAKER).post(f"{BASE}/bookings/{booking.pk}/decision",
                                          {"outcome": "approve"}, format="json")
    assert r.status_code == 403
    assert _status(booking) == "forwarded"


def test_the_incharge_cannot_skip_the_caretaker(act, world):
    booking = make_booking(status="pending")
    incharge = act(INCHARGE_ID, INCHARGE)
    assert incharge.post(f"{BASE}/bookings/{booking.pk}/decision",
                         {"outcome": "approve"}, format="json").status_code == 409
    assert incharge.post(f"{BASE}/bookings/{booking.pk}/review",
                         {"outcome": "forward"}, format="json").status_code == 403
    assert _status(booking) == "pending"


def test_a_permission_without_the_module_grant_is_refused(act, world):
    r = act(CARETAKER_ID, CARETAKER, modules=()).get(f"{BASE}/bookings")
    assert r.status_code == 403


def test_the_module_grant_without_the_permission_is_refused(act, world):
    r = act(INDENTER_ID, ()).post(f"{BASE}/bookings", requisition(), format="json")
    assert r.status_code == 403
    assert not Booking.objects.exists()


def test_a_second_caretaker_who_is_not_on_duty_cannot_act(act, world):
    """BR-VH-045: one Caretaker at a time, even if two people hold the designation."""
    booking = make_booking(status="pending")
    r = act(501, CARETAKER).post(f"{BASE}/bookings/{booking.pk}/review",
                                 {"outcome": "forward"}, format="json")
    assert r.status_code == 403 and r.data["error"]["code"] == "not_on_duty"
    assert _status(booking) == "pending"


def test_with_nobody_on_duty_the_refusal_says_what_to_do(act, db):
    booking = make_booking(status="pending")
    r = act(CARETAKER_ID, CARETAKER).post(f"{BASE}/bookings/{booking.pk}/review",
                                          {"outcome": "forward"}, format="json")
    assert r.status_code == 409 and "vh_assign_duty" in r.data["error"]["message"]


def test_nobody_decides_a_booking_they_raised(act, world):
    """The Caretaker on duty books their own guest; another officer must review it."""
    booking = make_booking(status="pending", indenter=CARETAKER_ID)
    r = act(CARETAKER_ID, CARETAKER).post(f"{BASE}/bookings/{booking.pk}/review",
                                          {"outcome": "forward"}, format="json")
    assert r.status_code == 403 and r.data["error"]["code"] == "self_decision"


def test_acting_as_faculty_a_caretaker_gets_only_the_indenter_view(act, world):
    """The role switch: two designations, one acting role, that role's grants only."""
    other = make_booking(status="pending", indenter=INDENTER_ID)
    mine = make_booking(status="pending", indenter=CARETAKER_ID)
    client = act(CARETAKER_ID, INDENTER, roles=("faculty", "VhCaretaker"),
                 active_role="faculty")
    listed = client.get(f"{BASE}/bookings").data["results"]
    assert [b["id"] for b in listed] == [mine.pk]
    assert client.get(f"{BASE}/bookings/{other.pk}").status_code == 404
    assert client.post(f"{BASE}/bookings/{other.pk}/review", {"outcome": "forward"},
                       format="json").status_code == 403


def test_an_indenter_cannot_record_an_offline_booking(act, world):
    r = act(INDENTER_ID, INDENTER).post(
        f"{BASE}/bookings/offline", {**requisition(), "source": "walk_in"}, format="json")
    assert r.status_code == 403


def test_an_indenter_cannot_bill_settle_or_touch_inventory(act, world):
    from django.utils import timezone
    booking = make_booking(status="checked_out", checked_in_at=timezone.now(),
                           checked_out_at=timezone.now())
    indenter = act(INDENTER_ID, INDENTER)
    assert indenter.post(f"{BASE}/bookings/{booking.pk}/bill").status_code == 403
    assert indenter.post(f"{BASE}/inventory", {"name": "Towels", "kind": "linen"},
                         format="json").status_code == 403
    assert indenter.post(f"{BASE}/rooms", {"number": "999", "room_type": "suite"},
                         format="json").status_code == 403
    assert not InventoryItem.objects.exists()
    assert not Room.objects.filter(number="999").exists()


def test_the_incharge_reviews_bills_but_cannot_settle_them(act, world):
    incharge = act(INCHARGE_ID, INCHARGE)
    assert incharge.get(f"{BASE}/bills").status_code == 200
    assert incharge.post(f"{BASE}/bills/1/settle", {"amount": "1.00"},
                         format="json").status_code == 403


def test_nobody_can_record_a_tariff_or_reassign_duty_over_http_yet(act, world):
    """UC-VH-011 and UC-VH-019 have no named authority."""
    payload = {"kind": "room", "category": "A", "occupancy": "single", "rate": "1",
               "effective_from": "2030-01-01"}
    for uid, perms in ((CARETAKER_ID, CARETAKER), (INCHARGE_ID, INCHARGE)):
        assert act(uid, perms).post(f"{BASE}/tariffs", payload,
                                    format="json").status_code == 403
    assert act(CARETAKER_ID, CARETAKER).get(f"{BASE}/tariffs").status_code == 200


def test_an_offline_booking_cannot_claim_an_online_source(act, world):
    r = act(CARETAKER_ID, CARETAKER).post(
        f"{BASE}/bookings/offline", {**requisition(), "source": "online"}, format="json")
    assert r.status_code == 400
