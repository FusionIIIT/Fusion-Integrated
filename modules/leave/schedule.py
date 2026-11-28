"""Celery beat timers and task routing for leave module."""

from celery.schedules import crontab

BEAT_SCHEDULE = {
    "leave-process-sla-hourly": {
        "task": "modules.leave.tasks.process_sla",
        "schedule": crontab(minute="0"),
    },
    "leave-yearend-daily": {
        "task": "modules.leave.tasks.process_year_end",
        "schedule": crontab(hour="0", minute="30"),
    },
}

TASK_ROUTES = {
    "modules.leave.tasks.*": {"queue": "leave"},
}
