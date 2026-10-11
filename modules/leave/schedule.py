"""Timers owned by the leave module (SF-EL-001, SF-EL-002)."""
from celery.schedules import crontab

TASK_ROUTES = {
    "leave.deliver_notifications": {"queue": "notifications"},
}

BEAT_SCHEDULE = {
    "leave.deliver-notifications": {
        "task": "leave.deliver_notifications",
        "schedule": 60.0,
        "options": {"expires": 55},
    },
    "leave.process-sla": {
        "task": "leave.process_sla",
        "schedule": 300.0,
        "options": {"expires": 290},
    },
    "leave.year-end": {
        "task": "leave.run_year_end",
        "schedule": crontab(minute=30, hour=1, day_of_month=1, month_of_year=1),
        "options": {"expires": 3600},
    },
}
