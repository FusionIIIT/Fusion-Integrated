"""What ELM needs run on a timer. Tasks are named by string, as placement does."""
from celery.schedules import crontab

TASK_ROUTES = {
    "elm.sla_sweep": {"queue": "notifications"},
}

BEAT_SCHEDULE = {
    "elm.sla-sweep": {
        "task": "elm.sla_sweep",
        "schedule": crontab(minute=5, hour="*/1"),
        "options": {"expires": 3000},
    },
    # Run just after the new year starts, for the year that ended.
    "elm.year-end": {
        "task": "elm.year_end",
        "schedule": crontab(minute=30, hour=1, day_of_month=1, month_of_year=1),
        "options": {"expires": 43200},
    },
}
