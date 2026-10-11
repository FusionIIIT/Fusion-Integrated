"""Every beat entry elm registers is in the merged Celery schedule (Step 5.9)."""
from config.celery import app
from modules.elm import schedule


def test_every_elm_beat_entry_is_registered():
    merged = app.conf.beat_schedule
    assert schedule.BEAT_SCHEDULE
    for name, entry in schedule.BEAT_SCHEDULE.items():
        assert name in merged, f"{name} is not in the merged beat schedule"
        assert merged[name]["task"] == entry["task"]


def test_every_elm_task_route_is_registered():
    merged = app.conf.task_routes
    for pattern, route in schedule.TASK_ROUTES.items():
        assert merged.get(pattern) == route


def test_the_accrual_task_is_importable_by_its_registered_name():
    from modules.elm.tasks import grant_annual_leave

    assert grant_annual_leave.name == "modules.elm.tasks.grant_annual_leave"
