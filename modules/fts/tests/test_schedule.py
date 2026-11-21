"""Tests for FTS Celery beat schedule and queue routing."""
import pytest

from config.celery import app
from modules.fts.schedule import BEAT_SCHEDULE, TASK_ROUTES

pytestmark = pytest.mark.django_db


def test_every_fts_scheduled_task_is_registered():
    missing = [entry["task"] for entry in BEAT_SCHEDULE.values() if entry["task"] not in app.tasks]
    assert not missing, f"scheduled but not registered: {missing}"


def test_fts_cleanup_task_is_scheduled():
    assert "fts.cleanup_discarded_drafts" in [e["task"] for e in BEAT_SCHEDULE.values()]


@pytest.mark.parametrize("name,entry", sorted(BEAT_SCHEDULE.items()))
def test_fts_entry_expires_before_next_run(name, entry):
    assert entry["options"]["expires"] > 0


def test_fts_tasks_are_routed():
    assert "fts.cleanup_discarded_drafts" in TASK_ROUTES
    assert TASK_ROUTES["fts.cleanup_discarded_drafts"]["queue"] == "default"
