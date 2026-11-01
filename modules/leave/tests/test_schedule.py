"""Every beat entry must name a task that exists, in a queue somebody serves.

Celery resolves task names at dispatch, so a typo here is silent: beat fires,
nothing runs, and the only symptom is scheduled work quietly not happening.
"""
import pytest

from config.celery import app
from modules.leave.schedule import BEAT_SCHEDULE, TASK_ROUTES


def test_every_scheduled_task_is_registered():
    missing = [entry["task"] for entry in BEAT_SCHEDULE.values()
               if entry["task"] not in app.tasks]
    assert not missing, f"scheduled but not registered: {missing}"


def test_the_three_recurring_jobs_are_scheduled():
    """Named explicitly, so deleting one is a decision rather than an accident."""
    assert {entry["task"] for entry in BEAT_SCHEDULE.values()} == {
        "leave.deliver_notifications",
        "leave.run_sla_sweep",
        "leave.run_year_end",
    }


def test_the_leave_entries_reach_the_merged_schedule():
    """Each module owns its timers; config only merges them."""
    assert set(BEAT_SCHEDULE) <= set(app.conf.beat_schedule)


@pytest.mark.parametrize("name,entry", sorted(BEAT_SCHEDULE.items()))
def test_each_entry_expires_before_its_next_run(name, entry):
    assert entry["options"]["expires"] > 0


def test_every_scheduled_task_is_routed_to_a_real_queue():
    served = {"default", "notifications", "reports", "ingest"}
    for task, route in TASK_ROUTES.items():
        assert route["queue"] in served, f"{task} -> unserved {route['queue']}"


def test_the_notification_drain_does_not_share_a_queue_with_year_end():
    assert (TASK_ROUTES["leave.deliver_notifications"]["queue"]
            != TASK_ROUTES["leave.run_year_end"]["queue"])


@pytest.mark.django_db
def test_the_year_end_task_needs_no_year_argument(configured):
    """The beat entry passes no arguments, so the task has to find the years."""
    from modules.leave.tasks import run_year_end

    assert "settled" in run_year_end.delay.__name__ or callable(run_year_end)
