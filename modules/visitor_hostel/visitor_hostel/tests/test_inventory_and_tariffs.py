"""Inventory alerts (UC-VH-014/015/025) and tariff history (BR-VH-024)."""
from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from core.api.exceptions import BadRequestError, PermissionDeniedError
from modules.visitor_hostel.models import (
    Bill,
    InventoryAdjustment,
    InventoryAlert,
    NotificationOutbox,
    RoomTariff,
)
from modules.visitor_hostel.services import billing, configuration
from modules.visitor_hostel.services import duty as duty_service
from modules.visitor_hostel.services import inventory as inventory_service
from modules.visitor_hostel.tests.conftest import (
    BASE,
    CARETAKER,
    CARETAKER_ID,
    INCHARGE,
    INCHARGE_ID,
    ROOM_RATES,
    make_booking,
    principal,
)

pytestmark = [pytest.mark.django_db, pytest.mark.urls("modules.visitor_hostel.tests.urls")]


def test_a_low_stock_item_alerts_the_caretaker_once(act, world):
    caretaker = act(CARETAKER_ID, CARETAKER)
    item = caretaker.post(f"{BASE}/inventory", {"name": "Bath towels", "kind": "linen",
                                                "quantity": 10, "min_threshold": 5},
                          format="json").data
    assert not InventoryAlert.objects.exists()

    caretaker.post(f"{BASE}/inventory/{item['id']}/adjust",
                   {"delta": -6, "reason": "sent to laundry"}, format="json")
    caretaker.post(f"{BASE}/inventory/{item['id']}/adjust",
                   {"delta": -1, "reason": "damaged"}, format="json")
    assert InventoryAlert.objects.filter(resolved_at__isnull=True).count() == 1
    mail = NotificationOutbox.objects.get(topic="inventory.below_threshold")
    assert mail.recipient_user_id == CARETAKER_ID

    caretaker.post(f"{BASE}/inventory/{item['id']}/adjust",
                   {"delta": 10, "reason": "received"}, format="json")
    assert not InventoryAlert.objects.filter(resolved_at__isnull=True).exists()
    assert InventoryAdjustment.objects.filter(item_id=item["id"]).count() == 4


def test_stock_never_goes_negative(act, world):
    caretaker = act(CARETAKER_ID, CARETAKER)
    item = caretaker.post(f"{BASE}/inventory", {"name": "Soap", "kind": "consumable",
                                                "quantity": 2}, format="json").data
    r = caretaker.post(f"{BASE}/inventory/{item['id']}/adjust",
                       {"delta": -3, "reason": "issued"}, format="json")
    assert r.status_code == 409


def test_the_incharge_approves_what_the_caretaker_recorded(act, world):
    caretaker = act(CARETAKER_ID, CARETAKER)
    item = caretaker.post(f"{BASE}/inventory", {"name": "Bedsheets", "kind": "linen"},
                          format="json").data
    req = caretaker.post(f"{BASE}/replenishments",
                         {"item_id": item["id"], "quantity_required": 20},
                         format="json").data
    assert caretaker.post(f"{BASE}/replenishments/{req['id']}/approve").status_code == 403
    r = act(INCHARGE_ID, INCHARGE).post(f"{BASE}/replenishments/{req['id']}/approve")
    assert r.data["status"] == "approved"
    again = act(INCHARGE_ID, INCHARGE).post(f"{BASE}/replenishments/{req['id']}/approve")
    assert again.status_code == 409


def test_nobody_approves_their_own_requirement(world):
    """The one person on duty in both offices still cannot self-approve."""
    duty_service.assign(role="incharge", user_id=CARETAKER_ID,
                        valid_until=timezone.now() + timedelta(days=5))
    both = principal(CARETAKER_ID, (*CARETAKER, *INCHARGE))
    item = inventory_service.create_item(actor=both, name="Kettles", kind="utensils")
    req = inventory_service.raise_replenishment(actor=both, item_id=item.pk,
                                                quantity_required=2)
    with pytest.raises(PermissionDeniedError):
        inventory_service.approve_replenishment(requirement_id=req.pk, actor=both)


def test_a_new_tariff_leaves_an_existing_bill_alone(world):
    """BR-VH-024: the bill copied its rate; nothing re-reads the tariff."""
    booking = make_booking(status="checked_out", arrival_in=-2, nights=2,
                           checked_in_at=timezone.now() - timedelta(days=2),
                           checked_out_at=timezone.now())
    booking.allotments.create(room=world[0], occupancy="single",
                              allotted_by_user_id=CARETAKER_ID)
    caretaker = principal(CARETAKER_ID, CARETAKER)
    bill = billing.generate(booking_id=booking.pk, actor=caretaker)
    before = bill.total
    assert before == ROOM_RATES[("A", "single")] * 2

    configuration.add_room_tariff(category="A", occupancy="single",
                                  rate=Decimal("9999"),
                                  effective_from=timezone.localdate())
    assert Bill.objects.get(pk=bill.pk).total == before
    assert bill.lines.get().unit_rate == ROOM_RATES[("A", "single")]


def test_a_replacement_tariff_cannot_be_backdated(world):
    with pytest.raises(BadRequestError):
        configuration.add_room_tariff(category="A", occupancy="single",
                                      rate=Decimal("1"),
                                      effective_from=timezone.localdate()
                                      - timedelta(days=1))
    assert RoomTariff.objects.filter(category="A", occupancy="single").count() == 1


def test_a_missing_tariff_is_a_409_that_says_so(act, world):
    RoomTariff.objects.filter(category="B").delete()
    booking = make_booking(status="checked_out", category="B", arrival_in=-1, nights=1,
                           checked_in_at=timezone.now() - timedelta(days=1),
                           checked_out_at=timezone.now())
    booking.allotments.create(room=world[0], occupancy="single",
                              allotted_by_user_id=CARETAKER_ID)
    r = act(CARETAKER_ID, CARETAKER).post(f"{BASE}/bookings/{booking.pk}/bill")
    assert r.status_code == 409 and r.data["error"]["code"] == "tariff_missing"
