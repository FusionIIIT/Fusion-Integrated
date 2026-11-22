"""Every beat entry is merged into config/celery.py and names a registered task."""
from config.celery import app
from modules.gymkhana.schedule import BEAT_SCHEDULE, TASK_ROUTES


def test_every_entry_is_in_the_merged_schedule():
    for name, entry in BEAT_SCHEDULE.items():
        assert app.conf.beat_schedule[name] == entry


def test_every_scheduled_task_is_registered_and_routed():
    for entry in BEAT_SCHEDULE.values():
        assert entry["task"] in app.tasks
        assert app.conf.task_routes[entry["task"]] == TASK_ROUTES[entry["task"]]
        assert entry["options"]["expires"] > 0


def test_the_drain_is_the_one_scheduled_job():
    """AFR-GYM-013/015/025 depend on it."""
    assert {e["task"] for e in BEAT_SCHEDULE.values()} == {"gymkhana.deliver_notifications"}
    assert TASK_ROUTES["gymkhana.deliver_notifications"]["queue"] == "notifications"
