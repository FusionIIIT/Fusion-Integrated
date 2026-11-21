"""ELM's timers. EVT-01 and EVT-02 are clocks, so beat must run in production."""
from celery.schedules import crontab

TASK_ROUTES = {
    "leave.process_sla": {"queue": "notifications"},
}

BEAT_SCHEDULE = {
    # EL-UC-021: hourly is finer than any threshold, which is set in hours.
    "leave.process-sla": {
        "task": "leave.process_sla",
        "schedule": crontab(minute=5),
        "options": {"expires": 3000},
    },
    # EL-UC-020: just after midnight on 1 January, for the year that ended.
    "leave.year-end": {
        "task": "leave.year_end",
        "schedule": crontab(minute=30, hour=0, day_of_month=1, month_of_year=1),
    },
}
