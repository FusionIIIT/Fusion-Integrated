"""Schedule and task registration tests for SPACS."""

import modules.spacs.tasks  # noqa: F401
from config.celery import app
from modules.spacs.schedule import BEAT_SCHEDULE, TASK_ROUTES


def test_every_spacs_scheduled_task_is_registered():
    missing = [entry["task"] for entry in BEAT_SCHEDULE.values() if entry["task"] not in app.tasks]
    assert not missing, f"scheduled but not registered: {missing}"


def test_spacs_recurring_jobs_are_scheduled():
    assert {e["task"] for e in BEAT_SCHEDULE.values()} == {
        "spacs.check_sla_tasks",
        "spacs.close_expired_cycles",
    }


def test_each_spacs_entry_expires():
    for name, entry in BEAT_SCHEDULE.items():
        assert entry["options"]["expires"] > 0, f"{name} must have positive expires"


def test_spacs_task_routes_point_to_valid_queues():
    served = {"default", "notifications", "reports", "ingest"}
    for task, route in TASK_ROUTES.items():
        assert route["queue"] in served, f"{task} -> unserved {route['queue']}"
