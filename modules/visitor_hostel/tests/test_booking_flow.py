"""The ordinary cases end to end, through HTTP (CW-VH-01, CW-VH-02, BW-VH-10)."""
from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from modules.visitor_hostel.models import (
    Bill,
    Booking,
    BookingTransition,
    NotificationOutbox,
    StayAlert,
)
from modules.visitor_hostel.services import stays
from modules.visitor_hostel.tests.conftest import (
    BASE,
    CARETAKER,
    CARETAKER_ID,
    INCHARGE,
    INCHARGE_ID,
    INDENTER,
    INDENTER_ID,
    MEAL_RATES,
    ROOM_RATES,
    make_booking,
    requisition,
)

pytestmark = [pytest.mark.django_db, pytest.mark.urls("modules.visitor_hostel.tests.urls")]

A_SINGLE = ROOM_RATES[("A", "single")]


def _approved_today(act, world):
    """An online booking for today, through the whole decision path."""
    today = timezone.localdate()
    r = act(INDENTER_ID, INDENTER).post(f"{BASE}/bookings", requisition(
        arrival_date=today.isoformat(),
        departure_date=(today + timedelta(days=2)).isoformat()), format="json")
    assert r.status_code == 201, r.data
    pk = r.data["id"]
    assert act(CARETAKER_ID, CARETAKER).post(
        f"{BASE}/bookings/{pk}/review", {"outcome": "forward"}, format="json"
    ).status_code == 200
    r = act(INCHARGE_ID, INCHARGE).post(
        f"{BASE}/bookings/{pk}/decision", {"outcome": "approve"}, format="json")
    assert r.data["status"] == "approved"
    return pk


def test_a_faculty_member_books_and_the_guest_stays_and_pays(act, world):
    """BW-VH-02 then BW-VH-10, then UC-VH-012/013/021."""
    pk = _approved_today(act, world)
    caretaker = act(CARETAKER_ID, CARETAKER)

    free = caretaker.get(f"{BASE}/bookings/{pk}/availability").data
    assert [r["number"] for r in free] == ["101", "102", "201"]

    r = caretaker.post(f"{BASE}/bookings/{pk}/allot",
                       {"rooms": [{"room_id": world[0].pk, "occupancy": "single"}]},
                       format="json")
    assert r.status_code == 200 and r.data["status"] == "room_allotted"
    assert caretaker.post(f"{BASE}/bookings/{pk}/check-in", {}, format="json"
                          ).data["status"] == "checked_in"

    today = timezone.localdate().isoformat()
    for meal in ({"meal_date": today, "kind": "individual", "item": "breakfast",
                  "quantity": 2},
                 {"meal_date": today, "kind": "add_on", "item": "tea"}):
        assert caretaker.post(f"{BASE}/bookings/{pk}/meals", meal,
                              format="json").status_code == 201

    assert caretaker.post(f"{BASE}/bookings/{pk}/check-out", {}, format="json"
                          ).data["status"] == "checked_out"

    bill = caretaker.post(f"{BASE}/bookings/{pk}/bill", format="json").data
    expected_meals = MEAL_RATES["breakfast"] * 2 + MEAL_RATES["tea"]
    assert Decimal(bill["room_amount"]) == A_SINGLE           # same-day: one day
    assert Decimal(bill["meal_amount"]) == expected_meals
    assert Decimal(bill["total"]) == A_SINGLE + expected_meals
    assert bill["billing_responsibility"] == "institute"

    wrong = caretaker.post(f"{BASE}/bills/{bill['id']}/settle", {"amount": "1.00"},
                           format="json")
    assert wrong.status_code == 409
    ok = caretaker.post(f"{BASE}/bills/{bill['id']}/settle",
                        {"amount": bill["total"], "receipt_reference": "R-1"},
                        format="json")
    assert ok.data["status"] == "settled" and ok.data["settlement_mode"] == "cash"
    assert caretaker.post(f"{BASE}/bills/{bill['id']}/settle", {"amount": bill["total"]},
                          format="json").status_code == 409
    assert caretaker.post(f"{BASE}/bills/{bill['id']}/verify", {"note": "checked"},
                          format="json").data["guest_verified"] is True

    detail = act(INDENTER_ID, INDENTER).get(f"{BASE}/bookings/{pk}").data
    assert [h["to_status"] for h in detail["history"]] == [
        "pending", "forwarded", "approved", "room_allotted", "checked_in", "checked_out"]
    assert detail["bill"]["status"] == "settled"
    topics = set(NotificationOutbox.objects.values_list("topic", flat=True))
    assert {"booking.submitted", "booking.approved"} <= topics


def test_a_bill_is_generated_once(act, world):
    pk = _approved_today(act, world)
    caretaker = act(CARETAKER_ID, CARETAKER)
    caretaker.post(f"{BASE}/bookings/{pk}/allot",
                   {"rooms": [{"room_id": world[0].pk, "occupancy": "single"}]},
                   format="json")
    caretaker.post(f"{BASE}/bookings/{pk}/check-in", {}, format="json")
    caretaker.post(f"{BASE}/bookings/{pk}/check-out", {}, format="json")
    assert caretaker.post(f"{BASE}/bookings/{pk}/bill").status_code == 201
    r = caretaker.post(f"{BASE}/bookings/{pk}/bill")
    assert r.status_code == 409 and r.data["error"]["code"] == "already_billed"


def test_the_caretaker_rejects_directly_with_a_reason(act, world):
    """BW-VH-01."""
    pk = act(INDENTER_ID, INDENTER).post(f"{BASE}/bookings", requisition(),
                                         format="json").data["id"]
    caretaker = act(CARETAKER_ID, CARETAKER)
    no_reason = caretaker.post(f"{BASE}/bookings/{pk}/review", {"outcome": "reject"},
                               format="json")
    assert no_reason.status_code == 409
    r = caretaker.post(f"{BASE}/bookings/{pk}/review",
                       {"outcome": "reject", "reason": "Hostel closed for repairs"},
                       format="json")
    assert r.data["status"] == "rejected"
    assert NotificationOutbox.objects.filter(topic="booking.rejected",
                                             recipient_user_id=INDENTER_ID).exists()


def test_an_offline_booking_is_flagged_and_routed_like_any_other(act, world):
    """BW-VH-05: BR-VH-003, 004, 005."""
    data = {**requisition(), "source": "walk_in"}
    r = act(CARETAKER_ID, CARETAKER).post(f"{BASE}/bookings/offline", data, format="json")
    assert r.status_code == 201
    assert (r.data["is_offline"], r.data["source"], r.data["status"]) == (
        True, "walk_in", "pending")
    pk = r.data["id"]
    act(CARETAKER_ID, CARETAKER).post(f"{BASE}/bookings/{pk}/review",
                                      {"outcome": "forward"}, format="json")
    r = act(INCHARGE_ID, INCHARGE).post(f"{BASE}/bookings/{pk}/decision",
                                        {"outcome": "approve"}, format="json")
    assert r.data["status"] == "approved" and r.data["is_offline"] is True
    filtered = act(INCHARGE_ID, INCHARGE).get(f"{BASE}/bookings?offline=true").data
    assert [b["id"] for b in filtered["results"]] == [pk]


def test_rooms_cannot_be_allotted_before_approval(act, world):
    """BR-VH-012."""
    booking = make_booking(status="forwarded")
    r = act(CARETAKER_ID, CARETAKER).post(
        f"{BASE}/bookings/{booking.pk}/allot",
        {"rooms": [{"room_id": world[0].pk, "occupancy": "single"}]}, format="json")
    assert r.status_code == 409
    assert not booking.allotments.exists()


def test_a_room_is_not_allotted_twice_for_overlapping_dates(act, world):
    first = make_booking(status="approved", arrival_in=5, nights=3)
    second = make_booking(status="approved", arrival_in=6, nights=3,
                          indenter=1002)
    caretaker = act(CARETAKER_ID, CARETAKER)
    room = {"rooms": [{"room_id": world[0].pk, "occupancy": "single"}]}
    assert caretaker.post(f"{BASE}/bookings/{first.pk}/allot", room,
                          format="json").status_code == 200
    r = caretaker.post(f"{BASE}/bookings/{second.pk}/allot", room, format="json")
    assert r.status_code == 409 and r.data["error"]["code"] == "room_unavailable"
    free = caretaker.get(f"{BASE}/bookings/{second.pk}/availability").data
    assert world[0].number not in [x["number"] for x in free]


def test_the_wrong_number_of_rooms_is_refused(act, world):
    booking = make_booking(status="approved", rooms_required=2)
    r = act(CARETAKER_ID, CARETAKER).post(
        f"{BASE}/bookings/{booking.pk}/allot",
        {"rooms": [{"room_id": world[0].pk, "occupancy": "single"}]}, format="json")
    assert r.data["error"]["code"] == "room_count_mismatch"


# -- Cancellation (CW-VH-02) ---------------------------------------------------
@pytest.mark.parametrize(("arrival_in", "case", "charge"), [
    (7, "seven_days", Decimal("0")),
    (3, "within_seven_days", A_SINGLE * Decimal("0.25")),
    (0, "same_day", A_SINGLE * Decimal("0.50")),
    (20, "beyond_schedule", Decimal("0")),
])
def test_cancellation_charge_and_billing_adjustment(act, world, arrival_in, case, charge):
    booking = make_booking(status="approved", arrival_in=arrival_in)
    r = act(INDENTER_ID, INDENTER).post(f"{BASE}/bookings/{booking.pk}/cancellation",
                                        {"reason": "Visit postponed"}, format="json")
    assert r.status_code == 201
    assert r.data["charge_case"] == case
    assert Decimal(r.data["charge_amount"]) == charge
    booking.refresh_from_db()
    assert booking.status == "approved"                 # not cancelled until confirmed

    r = act(CARETAKER_ID, CARETAKER).post(
        f"{BASE}/bookings/{booking.pk}/cancellation/confirm")
    assert r.status_code == 200 and r.data["status"] == "cancelled"
    bill = Bill.objects.filter(booking=booking).first()
    if charge:
        assert bill.cancellation_amount == charge and bill.total == charge
    else:
        assert bill is None


def test_a_booking_is_cancelled_only_once(act, world):
    booking = make_booking(status="pending")
    indenter = act(INDENTER_ID, INDENTER)
    assert indenter.post(f"{BASE}/bookings/{booking.pk}/cancellation").status_code == 201
    assert indenter.post(f"{BASE}/bookings/{booking.pk}/cancellation").status_code == 409


def test_confirming_without_a_request_is_refused(act, world):
    booking = make_booking(status="approved")
    r = act(CARETAKER_ID, CARETAKER).post(
        f"{BASE}/bookings/{booking.pk}/cancellation/confirm")
    assert r.status_code == 409 and r.data["error"]["code"] == "no_cancellation_request"


def test_a_checked_in_stay_cannot_be_cancelled(act, world):
    booking = make_booking(status="checked_in", arrival_in=0,
                           checked_in_at=timezone.now())
    r = act(INDENTER_ID, INDENTER).post(f"{BASE}/bookings/{booking.pk}/cancellation")
    assert r.status_code == 409


# -- No-show (BR-VH-017, BR-VH-009) --------------------------------------------
def test_a_no_show_is_alerted_and_billed_half_a_day(act, world):
    booking = make_booking(status="room_allotted", arrival_in=0)
    booking.allotments.create(room=world[0], occupancy="single",
                              allotted_by_user_id=CARETAKER_ID)
    assert stays.scan(now=timezone.now())["no_show"] == 0       # not yet end of day
    tomorrow = timezone.now() + timedelta(days=1)
    assert stays.scan(now=tomorrow)["no_show"] == 1
    assert stays.scan(now=tomorrow)["no_show"] == 0              # once per booking

    alerts = act(CARETAKER_ID, CARETAKER).get(f"{BASE}/alerts").data["results"]
    assert [a["kind"] for a in alerts] == ["no_show"]
    bill = act(CARETAKER_ID, CARETAKER).post(f"{BASE}/bookings/{booking.pk}/bill").data
    assert Decimal(bill["cancellation_amount"]) == A_SINGLE / 2
    assert Decimal(bill["room_amount"]) == 0


def test_an_overstay_is_alerted(world):
    booking = make_booking(status="checked_in", arrival_in=-2, nights=1,
                           checked_in_at=timezone.now() - timedelta(days=2))
    assert stays.scan()["overstay"] == 1
    assert StayAlert.objects.get(booking=booking).kind == "overstay"


def test_reminders_go_to_the_indenter_once(world):
    make_booking(status="approved", arrival_in=1)
    assert stays.send_reminders()["checkin"] == 1
    assert stays.send_reminders()["checkin"] == 0
    assert NotificationOutbox.objects.get(topic="stay.checkin_reminder"
                                          ).recipient_user_id == INDENTER_ID


# -- Modification (UC-VH-006, UC-VH-022) ---------------------------------------
def test_a_modification_waits_for_a_confirming_authority(act, world):
    booking = make_booking(status="approved")
    new_departure = (booking.departure_date + timedelta(days=1)).isoformat()
    r = act(INDENTER_ID, INDENTER).post(f"{BASE}/bookings/{booking.pk}/modifications",
                                        {"departure_date": new_departure}, format="json")
    assert r.status_code == 201
    mod_id = r.data["id"]

    # Nobody holds the authority yet, the Caretaker included.
    assert act(CARETAKER_ID, CARETAKER).post(
        f"{BASE}/modifications/{mod_id}/confirm").status_code == 403
    booking.refresh_from_db()
    assert booking.departure_date.isoformat() != new_departure

    # Once the institute grants it, confirmation applies the change.
    r = act(INCHARGE_ID, (*INCHARGE, "visitor_hostel.modification.approve")).post(
        f"{BASE}/modifications/{mod_id}/confirm")
    assert r.status_code == 200 and r.data["status"] == "confirmed"
    booking.refresh_from_db()
    assert booking.departure_date.isoformat() == new_departure
    assert BookingTransition.objects.filter(booking=booking,
                                            reason__contains="modification").exists()


def test_a_bad_query_parameter_is_a_400(act, world):
    caretaker = act(CARETAKER_ID, CARETAKER)
    assert caretaker.get(f"{BASE}/bookings?status=nonsense").status_code == 400
    incharge = act(INCHARGE_ID, INCHARGE)
    assert incharge.get(f"{BASE}/reports/incharge/revenue?from=abc").status_code == 400


def test_every_listed_report_answers(act, world):
    make_booking(status="pending")
    incharge = act(INCHARGE_ID, INCHARGE)
    for kind in ("booking-summary", "category-occupancy", "revenue", "inventory-usage"):
        assert incharge.get(f"{BASE}/reports/incharge/{kind}").status_code == 200, kind
    caretaker = act(CARETAKER_ID, CARETAKER)
    for kind in ("daily-occupancy", "arrivals-departures", "pending-approvals",
                 "no-show-overstay"):
        assert caretaker.get(f"{BASE}/reports/operations/{kind}").status_code == 200, kind
    pending = caretaker.get(f"{BASE}/reports/operations/pending-approvals").data
    assert len(pending["bookings"]) == Booking.objects.filter(status="pending").count()
