"""Every beat entry must name a task that is registered with Celery."""

from __future__ import annotations

import pytest

from config.celery import app
from modules.superadmin import tasks as _sa_tasks
from modules.superadmin.schedule import BEAT_SCHEDULE, TASK_ROUTES

# Reference imported tasks so Celery registers them before the lookup
_ = _sa_tasks


def test_every_scheduled_task_is_registered():
    missing = [entry["task"] for entry in BEAT_SCHEDULE.values() if entry["task"] not in app.tasks]
    assert not missing, f"scheduled but not registered: {missing}"


def test_the_three_recurring_jobs_are_scheduled():
    # Deleting a sweep silently stops it; named here so the removal is explicit.
    assert {e["task"] for e in BEAT_SCHEDULE.values()} == {
        "modules.superadmin.tasks.expire_reversibility_window_task",
        "modules.superadmin.tasks.expire_pending_purge_requests_task",
        "modules.superadmin.tasks.drain_notification_outbox_task",
    }


def test_beat_schedule_has_exactly_three_entries():
    assert len(BEAT_SCHEDULE) == 3


@pytest.mark.parametrize("name,entry", sorted(BEAT_SCHEDULE.items()))
def test_each_entry_has_a_schedule(name, entry):
    # Ensures beat fires rather than hanging on missing schedule key
    assert entry.get("schedule") is not None and entry["schedule"] > 0


def test_all_routes_target_superadmin_queue():
    for task, route in TASK_ROUTES.items():
        assert route["queue"] == "superadmin", (
            f"{task} routed to '{route['queue']}' — expected 'superadmin'"
        )


def test_drain_outbox_runs_more_frequently_than_archival_sweep():
    schedules = {e["task"]: e["schedule"] for e in BEAT_SCHEDULE.values()}
    drain = schedules["modules.superadmin.tasks.drain_notification_outbox_task"]
    sweep = schedules["modules.superadmin.tasks.expire_reversibility_window_task"]
    assert drain < sweep, "Outbox drain must run more frequently than the daily archival sweep."
