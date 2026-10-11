"""ELM-owned Celery queue and calendar schedules."""
from celery.schedules import crontab

TASK_ROUTES = {
    "leave.deliver_notifications": {"queue": "notifications"},
    "leave.process_sla": {"queue": "default"},
    "leave.process_year_end": {"queue": "default"},
    "leave.synchronize_resumption": {"queue": "default"},
}

BEAT_SCHEDULE = {
    "leave.deliver-notifications": {
        "task": "leave.deliver_notifications", "schedule": 60.0,
        "options": {"expires": 55},
    },
    "leave.process-sla": {
        "task": "leave.process_sla", "schedule": 300.0,
        "options": {"expires": 290},
    },
    "leave.year-end": {
        "task": "leave.process_year_end", "schedule": crontab(
            minute=0, hour=2, day_of_month=1, month_of_year=1),
        "options": {"expires": 3600},
    },
}
