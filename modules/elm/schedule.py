"""What this module needs run on a timer."""
from celery.schedules import crontab

TASK_ROUTES = {
    "elm.year_end": {"queue": "reports"},
}

BEAT_SCHEDULE = {
    # EL-UC-021: hourly is finer than any threshold an administrator can set.
    "elm.sla-sweep": {
        "task": "elm.sla_sweep",
        "schedule": crontab(minute=5),
        "options": {"expires": 3000},
    },
    # EL-UC-020: the year-end boundary is 1 January.
    "elm.year-end": {
        "task": "elm.year_end",
        "schedule": crontab(minute=30, hour=0, day_of_month=1, month_of_year=1),
    },
}
