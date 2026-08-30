"""SF: the calendar moves leave along, and nothing else does.

Nothing invoked these transitions, so an approved request stayed
APPROVED_NOT_STARTED for ever. That is not one bug but four: it never became
ONGOING, so it stayed cancellable after the employee had gone; extension is
only reachable while the leave runs, so it was unreachable; resumption never
opened; and nothing ever closed or restored a balance.
"""
from datetime import date
from io import StringIO

import pytest
from django.core.management import call_command

from core.api.exceptions import ConflictError
from modules.leave.domain.categories import Category
from modules.leave.domain.state_machine import State
from modules.leave.services import decisions, lifecycle, scheduler
from modules.leave.services import requests as service
from modules.leave.tests import factories
from modules.leave.tests.factories import YEAR

pytestmark = pytest.mark.django_db

U = 701
REGISTRAR = frozenset({"Registrar"})


def approved(start, end, category=Category.EL):
    factories.credit(U, category, 60)
    r = service.submit(user_id=U, category=category, starts_on=start, ends_on=end,
                       reason="x", unit="CSE", faculty=category is Category.VL,
                       designations=frozenset({"Assistant Professor"}))
    r = decisions.unit_head_decides(request=r, actor_user_id=900, approve=True)
    if r.state == State.AWAITING_ESTABLISHMENT.value:
        r = decisions.establishment_routes(request=r, actor_user_id=901)
    if r.state == State.AWAITING_FINAL_SANCTION.value:
        r = decisions.sanction(request=r, actor_user_id=902, approve=True,
                               actor_designations=REGISTRAR)
    assert r.state == State.APPROVED_NOT_STARTED.value
    return r


class TestWhatIsDue:
    def test_leave_starting_today_is_due_to_begin(self):
        factories.setup_all(999)
        r = approved(date(YEAR, 3, 2), date(YEAR, 3, 6))

        assert [x.pk for x in scheduler.due_to_begin(date(YEAR, 3, 2))] == [r.pk]

    def test_leave_starting_tomorrow_is_not(self):
        factories.setup_all(999)
        approved(date(YEAR, 3, 2), date(YEAR, 3, 6))

        assert scheduler.due_to_begin(date(YEAR, 3, 1)) == []

    def test_leave_still_running_on_its_last_day_is_not_due_to_end(self):
        factories.setup_all(999)
        r = approved(date(YEAR, 3, 2), date(YEAR, 3, 6))
        scheduler.advance(date(YEAR, 3, 2))
        r.refresh_from_db()

        # The last day is still leave.
        assert scheduler.due_to_end(date(YEAR, 3, 6)) == []
        assert scheduler.due_to_end(date(YEAR, 3, 7)) == [r]


class TestAdvancing:
    def test_it_starts_leave_and_records_the_scheduler_as_the_actor(self):
        factories.setup_all(999)
        r = approved(date(YEAR, 3, 2), date(YEAR, 3, 6))

        report = scheduler.advance(date(YEAR, 3, 2))

        r.refresh_from_db()
        assert report.started == 1
        assert r.state == State.ONGOING.value
        assert r.transitions.order_by("id").last().actor_role == "SCHEDULER"

    def test_it_opens_resumption_once_the_end_has_passed(self):
        factories.setup_all(999)
        r = approved(date(YEAR, 3, 2), date(YEAR, 3, 6))
        scheduler.advance(date(YEAR, 3, 2))

        scheduler.advance(date(YEAR, 3, 7))

        r.refresh_from_db()
        assert r.state == State.AWAITING_RESUMPTION.value

    def test_a_single_pass_can_start_and_end_different_requests(self):
        factories.setup_all(999)
        early = approved(date(YEAR, 3, 2), date(YEAR, 3, 4))
        later = approved(date(YEAR, 3, 9), date(YEAR, 3, 11))
        scheduler.advance(date(YEAR, 3, 2))

        report = scheduler.advance(date(YEAR, 3, 9))

        assert (report.started, report.ended) == (1, 1)
        early.refresh_from_db()
        later.refresh_from_db()
        assert early.state == State.AWAITING_RESUMPTION.value
        assert later.state == State.ONGOING.value

    def test_running_it_twice_moves_nothing_the_second_time(self):
        factories.setup_all(999)
        approved(date(YEAR, 3, 2), date(YEAR, 3, 6))
        scheduler.advance(date(YEAR, 3, 2))

        assert scheduler.advance(date(YEAR, 3, 2)).moved == 0

    def test_catching_up_after_the_worker_was_down(self):
        factories.setup_all(999)
        r = approved(date(YEAR, 3, 2), date(YEAR, 3, 6))

        # Nothing ran for a fortnight. One pass takes it the whole way, because
        # the end sweep runs after the start sweep and sees what it just moved.
        report = scheduler.advance(date(YEAR, 3, 20))

        r.refresh_from_db()
        assert (report.started, report.ended) == (1, 1)
        assert r.state == State.AWAITING_RESUMPTION.value


class TestWhatAdvancingUnblocks:
    def test_running_leave_can_no_longer_be_cancelled(self):
        factories.setup_all(999)
        r = approved(date(YEAR, 3, 2), date(YEAR, 3, 6))
        scheduler.advance(date(YEAR, 3, 2))
        r.refresh_from_db()

        # Before, leave stayed APPROVED_NOT_STARTED for ever and so stayed
        # cancellable long after the employee had gone.
        with pytest.raises(ConflictError):
            lifecycle.request_cancellation(request=r, actor_user_id=U)

    def test_extension_becomes_reachable(self):
        factories.setup_all(999)
        r = approved(date(YEAR, 3, 2), date(YEAR, 3, 6))
        scheduler.advance(date(YEAR, 3, 2))
        r.refresh_from_db()

        extended = lifecycle.request_extension(
            request=r, actor_user_id=U, new_end=date(YEAR, 3, 10))

        assert extended.state.startswith("EXTENSION")

    def test_the_request_can_reach_closure(self):
        factories.setup_all(999)
        r = approved(date(YEAR, 3, 2), date(YEAR, 3, 6))
        scheduler.advance(date(YEAR, 3, 2))
        scheduler.advance(date(YEAR, 3, 7))
        r.refresh_from_db()

        r = lifecycle.submit_resumption(request=r, actor_user_id=U,
                                        resumed_on=date(YEAR, 3, 9))
        r = lifecycle.verify_resumption(request=r, actor_user_id=901)

        assert r.state == State.CLOSED.value


class TestTheCommand:
    def test_it_reports_what_is_due_without_moving_it(self):
        factories.setup_all(999)
        r = approved(date(YEAR, 3, 2), date(YEAR, 3, 6))
        out = StringIO()

        call_command("leave_advance", "--on", str(date(YEAR, 3, 2)), "--status",
                     stdout=out)

        assert "due to begin  1" in out.getvalue()
        r.refresh_from_db()
        assert r.state == State.APPROVED_NOT_STARTED.value

    def test_it_advances_and_says_what_it_did(self):
        factories.setup_all(999)
        approved(date(YEAR, 3, 2), date(YEAR, 3, 6))
        out = StringIO()

        call_command("leave_advance", "--on", str(date(YEAR, 3, 2)), stdout=out)

        assert "started   1" in out.getvalue()

    def test_it_says_so_when_nothing_is_due(self):
        factories.setup_all(999)
        out = StringIO()

        call_command("leave_advance", stdout=out)

        assert "nothing was due" in out.getvalue()


def test_the_beat_schedule_includes_both_timers():
    from modules.leave.schedule import BEAT_SCHEDULE

    tasks = {v["task"] for v in BEAT_SCHEDULE.values()}
    assert tasks == {"leave.advance_lifecycle", "leave.process_sla"}
    assert all("expires" in v["options"] for v in BEAT_SCHEDULE.values())


def test_the_schedule_is_merged_into_the_app():
    from config.celery import app

    assert "leave.advance-lifecycle" in app.conf.beat_schedule
    assert "leave.process-sla" in app.conf.beat_schedule
    # Placement's timers must survive the merge.
    assert "placement.expire-overdue-offers" in app.conf.beat_schedule


def test_the_tasks_exist_under_the_names_the_schedule_uses():
    from modules.leave import tasks

    assert tasks.advance_lifecycle.name == "leave.advance_lifecycle"
    assert tasks.process_sla.name == "leave.process_sla"


def test_leave_starting_in_the_far_future_is_left_alone():
    factories.setup_all(999)
    approved(date(YEAR, 12, 1), date(YEAR, 12, 5))

    assert scheduler.advance(date(YEAR, 3, 2)).moved == 0
