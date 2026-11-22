"""Schedule and Celery task tests for File Tracking System."""

import pytest

from config.celery import app
from modules.filetracking.schedule import BEAT_SCHEDULE, TASK_ROUTES
from modules.filetracking.tasks import (
    reconcile_outbox_notifications,
    verify_audit_integrity,
)


def test_every_scheduled_task_is_registered():
    missing = [
        entry["task"]
        for entry in BEAT_SCHEDULE.values()
        if entry["task"] not in app.tasks
    ]
    assert not missing, f"scheduled but not registered: {missing}"


def test_recurring_jobs_are_scheduled():
    assert {e["task"] for e in BEAT_SCHEDULE.values()} == {
        "modules.filetracking.tasks.reconcile_outbox_notifications",
        "modules.filetracking.tasks.verify_audit_integrity",
    }


@pytest.mark.parametrize("name,entry", sorted(BEAT_SCHEDULE.items()))
def test_each_entry_expires_before_its_next_run(name, entry):
    assert entry.get("options", {}).get("expires", 0) > 0


def test_every_scheduled_task_is_routed_to_a_real_queue():
    served = {"default", "notifications", "reports", "ingest"}
    for task, route in TASK_ROUTES.items():
        assert route["queue"] in served, f"{task} -> unserved {route['queue']}"


def test_tasks_run_directly():
    assert reconcile_outbox_notifications() == 0
    assert verify_audit_integrity() is True
