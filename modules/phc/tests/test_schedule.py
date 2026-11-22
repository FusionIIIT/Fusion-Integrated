"""PHC registers no timed work, and config merges its (empty) schedule like any module's."""
from config.celery import app
from modules.phc.schedule import BEAT_SCHEDULE, TASK_ROUTES


def test_phc_schedule_is_merged_into_celery():
    assert BEAT_SCHEDULE == {}
    assert TASK_ROUTES == {}
    for name in BEAT_SCHEDULE:
        assert name in app.conf.beat_schedule
