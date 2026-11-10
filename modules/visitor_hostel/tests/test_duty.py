"""Duty roster (BR-VH-045..050)."""
from datetime import timedelta

import pytest
from django.db import IntegrityError
from django.utils import timezone

from modules.visitor_hostel.models import Booking, DutyAssignment
from modules.visitor_hostel.services import duty as duty_service
from modules.visitor_hostel.tests.conftest import (
    BASE,
    CARETAKER,
    CARETAKER_ID,
    INCHARGE_ID,
    make_booking,
)

pytestmark = [pytest.mark.django_db, pytest.mark.urls("modules.visitor_hostel.tests.urls")]

NEW_CARETAKER = 501


def _later(days=30):
    return timezone.now() + timedelta(days=days)


def test_reassignment_moves_pending_and_ongoing_records(world):
    pending = make_booking(status="pending")
    ongoing = make_booking(status="room_allotted", indenter=1002)
    done = make_booking(status="checked_out", indenter=1002,
                        checked_in_at=timezone.now(), checked_out_at=timezone.now())

    result = duty_service.assign(role="caretaker", user_id=NEW_CARETAKER,
                                 valid_until=_later())

    assert result.previous_user_id == CARETAKER_ID
    assert (result.pending_transferred, result.ongoing_transferred) == (1, 1)
    owners = dict(Booking.objects.values_list("pk", "caretaker_user_id"))
    assert owners[pending.pk] == owners[ongoing.pk] == NEW_CARETAKER
    assert owners[done.pk] == CARETAKER_ID                    # history keeps its owner


def test_reassignment_takes_effect_immediately(act, world):
    """BR-VH-048: the outgoing Caretaker is refused on the very next request."""
    booking = make_booking(status="pending")
    duty_service.assign(role="caretaker", user_id=NEW_CARETAKER, valid_until=_later())

    old = act(CARETAKER_ID, CARETAKER).post(f"{BASE}/bookings/{booking.pk}/review",
                                            {"outcome": "forward"}, format="json")
    assert old.status_code == 403
    new = act(NEW_CARETAKER, CARETAKER).post(f"{BASE}/bookings/{booking.pk}/review",
                                             {"outcome": "forward"}, format="json")
    assert new.status_code == 200


def test_the_database_holds_one_open_assignment_per_role(world):
    with pytest.raises(IntegrityError):
        DutyAssignment.objects.create(role="incharge", user_id=999,
                                      valid_from=timezone.now(), valid_until=_later())


def test_an_expired_assignment_means_nobody_is_on_duty(act, world):
    """BR-VH-047: time-bound means it ends without anyone remembering to end it."""
    DutyAssignment.objects.filter(role="incharge").update(
        valid_until=timezone.now() - timedelta(seconds=1),
        valid_from=timezone.now() - timedelta(days=1))
    booking = make_booking(status="forwarded")
    from modules.visitor_hostel.tests.conftest import INCHARGE
    r = act(INCHARGE_ID, INCHARGE).post(f"{BASE}/bookings/{booking.pk}/decision",
                                        {"outcome": "approve"}, format="json")
    assert r.status_code == 409 and r.data["error"]["code"] == "no_one_on_duty"
    assert duty_service.close_lapsed() == 1


def test_an_assignment_must_end(world):
    from core.api.exceptions import BadRequestError

    with pytest.raises(BadRequestError):
        duty_service.assign(role="caretaker", user_id=1, valid_until=timezone.now()
                            - timedelta(days=1))
