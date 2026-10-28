"""Celery Beat declaration for scheduled ELM functions (SF-EL-001/002)."""

from celery.schedules import crontab

BEAT_SCHEDULE = {
    "elm.sla-processing": {
        "task": "elm.process_sla",
        "schedule": 300.0,
        "options": {"expires": 290},
    },
    "elm.year-end-processing": {
        "task": "elm.process_year_end",
        "schedule": crontab(minute=15, hour=2, day_of_month=1, month_of_year=1),
        "options": {"expires": 3500},
    },
}
TASK_ROUTES = {
    "elm.process_sla": {"queue": "notifications"},
    "elm.process_year_end": {"queue": "default"},
}
