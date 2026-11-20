"""Every beat entry must name a task that exists."""
import pytest

from config.celery import app
from modules.placement.schedule import BEAT_SCHEDULE


def test_every_scheduled_task_is_registered():
    missing = [entry["task"] for entry in BEAT_SCHEDULE.values()
               if entry["task"] not in app.tasks]
    assert not missing, f"scheduled but not registered: {missing}"


def test_the_three_recurring_jobs_are_scheduled():
    """Named explicitly, so deleting one is a decision rather than an accident."""
    assert {e["task"] for e in BEAT_SCHEDULE.values()} == {
        "placement.deliver_notifications",
        "placement.expire_overdue_offers",
        "placement.rebuild_active_stats",
    }


@pytest.mark.parametrize("name,entry", sorted(BEAT_SCHEDULE.items()))
def test_each_entry_expires_before_its_next_run(name, entry):
    """Without `expires`, a broker backlog replays every missed tick at once."""
    assert entry["options"]["expires"] > 0


@pytest.mark.django_db
def test_rebuild_active_stats_needs_no_season_argument():
    """The beat entry passes no arguments, so the task has to find the active seasons itself."""
    from modules.placement.models import PlacementPolicy
    from modules.placement.tasks import rebuild_active_stats

    PlacementPolicy.objects.create(season="2026-27", is_active=True)
    PlacementPolicy.objects.create(season="2019-20", is_active=False)

    assert rebuild_active_stats() >= 0


def test_every_scheduled_task_is_routed_to_a_real_queue():
    """The deployment runs one worker per queue."""
    from modules.placement.schedule import TASK_ROUTES

    served = {"default", "notifications", "reports", "ingest"}
    for task, route in TASK_ROUTES.items():
        assert route["queue"] in served, f"{task} -> unserved {route['queue']}"


def test_the_notification_drain_does_not_share_a_queue_with_reports():
    """A 15-minute stats rebuild must not sit in front of a student's offer email on one worker."""
    from modules.placement.schedule import TASK_ROUTES

    assert (TASK_ROUTES["placement.deliver_notifications"]["queue"]
            != TASK_ROUTES["placement.rebuild_active_stats"]["queue"])
