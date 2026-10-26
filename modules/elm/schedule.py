"""Scheduled tasks for ELM (SF-EL-001, SF-EL-002)."""
from celery.schedules import crontab

TASK_ROUTES = {
    "elm.year_end": {"queue": "default"},
    "elm.sla": {"queue": "default"},
}

BEAT_SCHEDULE = {
    "elm.year-end": {
        "task": "elm.year_end",
        "schedule": crontab(minute=30, hour=0, day_of_month=1, month_of_year=1),
    },
    "elm.sla": {
        "task": "elm.sla",
        "schedule": crontab(minute=0),
    },
}
