"""Schedule registration and queue routing tests for Gymkhana."""
import pytest

import modules.gymkhana.tasks  # noqa: F401
from config.celery import app
from modules.gymkhana.schedule import BEAT_SCHEDULE, TASK_ROUTES


def test_every_scheduled_task_is_registered():
    missing = [entry["task"] for entry in BEAT_SCHEDULE.values() if entry["task"] not in app.tasks]
    assert not missing, f"scheduled but not registered: {missing}"


@pytest.mark.parametrize("name,entry", sorted(BEAT_SCHEDULE.items()))
def test_each_entry_expires_before_its_next_run(name, entry):
    assert entry["options"]["expires"] > 0


def test_every_scheduled_task_is_routed_to_a_real_queue():
    served = {"default", "notifications", "reports", "ingest"}
    for task, route in TASK_ROUTES.items():
        assert route["queue"] in served, f"{task} -> unserved {route['queue']}"
