"""Celery beat schedule and task routing for patents module."""
from celery.schedules import crontab

TASK_ROUTES = {
    "patents.pms_sweep_deadlines": {"queue": "default"},
}

BEAT_SCHEDULE = {
    "patents.pms-sweep-deadlines": {
        "task": "patents.pms_sweep_deadlines",
        "schedule": crontab(hour=0, minute=30),  # Daily 00:30 UTC
        "options": {"expires": 3600},
    },
}
