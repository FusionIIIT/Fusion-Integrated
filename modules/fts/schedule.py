"""Celery beat schedule and task routes for FTS."""
from celery.schedules import crontab

TASK_ROUTES = {
    "fts.cleanup_discarded_drafts": {"queue": "default"},
}

BEAT_SCHEDULE = {
    "fts.cleanup-discarded-drafts": {
        "task": "fts.cleanup_discarded_drafts",
        "schedule": crontab(hour=3, minute=0),
        "options": {"expires": 3600},
    },
}
