from celery.schedules import crontab

BEAT_SCHEDULE = {
    "elm.sweep-sla": {"task": "modules.elm.tasks.sweep_sla", "schedule": 300.0},
    "elm.close-previous-year": {"task": "modules.elm.tasks.close_previous_year",
                              "schedule": crontab(hour=0, minute=15)},
}
