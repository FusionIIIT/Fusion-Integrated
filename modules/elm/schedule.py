"""This module's timers; config/celery.py merges them so elm stays removable.

The annual grant runs on 1 April: if it does not run, nobody's entitlement is
recorded for the year and the first request fails closed on the balance guard.
`TASK_ROUTES` sends the task to the default queue explicitly.
"""
from celery.schedules import crontab

BEAT_SCHEDULE = {
    "elm.grant-annual-leave": {
        "task": "modules.elm.tasks.grant_annual_leave",
        "schedule": crontab(minute=30, hour=0, day_of_month=1, month_of_year=4),
    },
}

TASK_ROUTES = {
    "modules.elm.tasks.*": {"queue": "default"},
}
