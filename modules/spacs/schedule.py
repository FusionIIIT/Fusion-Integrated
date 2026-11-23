"""Scheduled tasks and Celery beat configuration for SPACS."""

from celery.schedules import crontab

TASK_ROUTES = {
    "spacs.check_sla_tasks": {"queue": "default"},
    "spacs.close_expired_cycles": {"queue": "default"},
}

BEAT_SCHEDULE = {
    "spacs.check-sla-tasks-hourly": {
        "task": "spacs.check_sla_tasks",
        "schedule": crontab(minute=0),
        "options": {"expires": 3500},
    },
    "spacs.close-expired-cycles-daily": {
        "task": "spacs.close_expired_cycles",
        "schedule": crontab(hour=0, minute=5),
        "options": {"expires": 7200},
    },
}
