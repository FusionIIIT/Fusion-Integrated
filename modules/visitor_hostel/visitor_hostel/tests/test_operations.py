"""Schedule wiring, query budgets, readiness, contracts and concurrency."""
import threading
from datetime import timedelta

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from modules.visitor_hostel import contracts, registry
from modules.visitor_hostel.schedule import BEAT_SCHEDULE, TASK_ROUTES
from modules.visitor_hostel.tests.conftest import (
    BASE,
    CARETAKER,
    CARETAKER_ID,
    INDENTER_ID,
    make_booking,
)

pytestmark = [pytest.mark.django_db, pytest.mark.urls("modules.visitor_hostel.tests.urls")]


def test_every_scheduled_task_is_registered():
    from celery import current_app

    import modules.visitor_hostel.tasks  # noqa: F401

    missing = [e["task"] for e in BEAT_SCHEDULE.values()
               if e["task"] not in current_app.tasks]
    assert not missing


def test_the_four_recurring_jobs_are_scheduled():
    assert {e["task"] for e in BEAT_SCHEDULE.values()} == {
        "visitor_hostel.deliver_notifications", "visitor_hostel.scan_stays",
        "visitor_hostel.send_stay_reminders", "visitor_hostel.close_lapsed_duty"}
    assert all(e["options"]["expires"] > 0 for e in BEAT_SCHEDULE.values())
    assert TASK_ROUTES["visitor_hostel.deliver_notifications"]["queue"] == "notifications"


def test_the_merged_platform_schedule_carries_these_entries():
    """Fails until config/celery.py merges this module's BEAT_SCHEDULE."""
    from config.celery import app

    if not set(BEAT_SCHEDULE) & set(app.conf.beat_schedule):
        pytest.xfail("config/celery.py does not merge visitor_hostel's schedule yet")
    assert set(BEAT_SCHEDULE) <= set(app.conf.beat_schedule)


def test_the_booking_list_costs_the_same_for_more_rows(act, world):
    client = act(CARETAKER_ID, CARETAKER)
    for _ in range(3):
        make_booking()
    with CaptureQueriesContext(connection) as few:
        assert client.get(f"{BASE}/bookings").status_code == 200
    for _ in range(6):
        make_booking()
    with CaptureQueriesContext(connection) as many:
        client.get(f"{BASE}/bookings")
    assert len(many) == len(few)


def test_the_booking_detail_costs_the_same_for_a_full_history(act, world):
    small = make_booking(status="checked_in", arrival_in=0, checked_in_at=timezone.now())
    small.allotments.create(room=world[0], occupancy="single",
                            allotted_by_user_id=CARETAKER_ID)
    big = make_booking(status="checked_in", arrival_in=0, indenter=1002,
                       checked_in_at=timezone.now())
    for room in world[1:]:
        big.allotments.create(room=room, occupancy="single",
                              allotted_by_user_id=CARETAKER_ID)
    client = act(CARETAKER_ID, CARETAKER)
    with CaptureQueriesContext(connection) as a:
        client.get(f"{BASE}/bookings/{small.pk}")
    with CaptureQueriesContext(connection) as b:
        client.get(f"{BASE}/bookings/{big.pk}")
    assert len(a) == len(b)


def test_readiness_names_what_is_missing(db):
    unmet = registry.readiness()
    assert any("rooms" in u for u in unmet)
    assert any("Caretaker" in u for u in unmet)


def test_readiness_is_clear_once_set_up(world):
    assert registry.readiness() == []


def test_the_contract_answers_for_every_id_asked(world):
    make_booking(indenter=INDENTER_ID)
    got = contracts.get_indenter_summaries([INDENTER_ID, 4242])
    assert got[INDENTER_ID].open_bookings == 1
    assert got[4242].open_bookings == 0


@pytest.mark.django_db(transaction=True)
def test_two_caretakers_cannot_allot_one_room_twice_at_once(world):
    """Real threads against a real database. SQLite serialises writes, so this
    proves the lock only on PostgreSQL."""
    if connection.vendor != "postgresql":
        pytest.skip("row locks need PostgreSQL")
    from core.api.exceptions import DomainError
    from modules.visitor_hostel.services import bookings as booking_service
    from modules.visitor_hostel.tests.conftest import principal

    a = make_booking(status="approved", arrival_in=3)
    b = make_booking(status="approved", arrival_in=3, indenter=1002)
    actor = principal(CARETAKER_ID, CARETAKER)
    results, barrier = [], threading.Barrier(2)

    def go(booking):
        barrier.wait()
        try:
            booking_service.allot_rooms(booking_id=booking.pk, actor=actor,
                                        rooms=[{"room_id": world[0].pk,
                                                "occupancy": "single"}])
            results.append("ok")
        except DomainError as exc:
            results.append(exc.code)
        finally:
            connection.close()

    threads = [threading.Thread(target=go, args=(x,)) for x in (a, b)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(results) == ["ok", "room_unavailable"]


def test_scan_runs_quietly_when_there_is_nothing_to_do(world):
    from modules.visitor_hostel.services import stays

    assert stays.scan(now=timezone.now() + timedelta(days=1)) == {"no_show": 0,
                                                                   "overstay": 0}
