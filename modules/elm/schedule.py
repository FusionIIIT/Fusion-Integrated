from celery.schedules import crontab

TASK_ROUTES = {
    "elm.process_year_end": {"queue": "default"},
    "elm.process_sla": {"queue": "default"},
}

BEAT_SCHEDULE = {
    "elm.year-end": {
        "task": "elm.process_year_end",
        "schedule": crontab(minute=30, hour=0, day_of_month=1, month_of_year=1),
        "options": {"expires": 3600},
    },
    "elm.sla-hourly": {
        "task": "elm.process_sla",
        "schedule": 3600.0,
        "options": {"expires": 3500},
    },
}
