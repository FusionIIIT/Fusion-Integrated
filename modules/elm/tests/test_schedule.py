import modules.elm.tasks  # noqa: F401
from config.celery import app
from modules.elm.schedule import BEAT_SCHEDULE


def test_every_scheduled_task_is_registered():
    missing = [e["task"] for e in BEAT_SCHEDULE.values() if e["task"] not in app.tasks]
    assert not missing


def test_elm_entries_are_merged_into_the_platform_schedule():
    for name in BEAT_SCHEDULE:
        assert name in app.conf.beat_schedule


def test_year_end_and_sla_are_scheduled():
    assert {e["task"] for e in BEAT_SCHEDULE.values()} == {"elm.year_end", "elm.sla"}
