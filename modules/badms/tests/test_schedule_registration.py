from config.celery import app
from modules.badms.schedule import BEAT_SCHEDULE


def test_every_badms_beat_entry_is_merged_into_celery_app():
    for name, entry in BEAT_SCHEDULE.items():
        assert app.conf.beat_schedule[name] == entry
