"""The PMS beat schedule must register and route every declared task."""

from config.celery import app
from modules.pms.schedule import BEAT_SCHEDULE, TASK_ROUTES


def test_every_pms_scheduled_task_is_registered():
    app.loader.import_default_modules()
    missing = [entry["task"] for entry in BEAT_SCHEDULE.values() if entry["task"] not in app.tasks]
    assert not missing, f"scheduled but not registered: {missing}"


def test_pms_deadline_monitor_and_notification_drain_are_scheduled():
    assert {entry["task"] for entry in BEAT_SCHEDULE.values()} == {
        "pms.monitor_deadlines",
        "pms.deliver_notifications",
    }


def test_pms_schedule_entries_expire_before_the_next_run():
    assert all(entry["options"]["expires"] > 0 for entry in BEAT_SCHEDULE.values())


def test_pms_task_routes_target_running_worker_queues():
    served = {"default", "notifications", "reports", "ingest"}
    assert all(route["queue"] in served for route in TASK_ROUTES.values())
