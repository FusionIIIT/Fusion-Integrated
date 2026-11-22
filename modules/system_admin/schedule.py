"""Celery beat schedule and task routes for System Admin."""
from celery.schedules import crontab

TASK_ROUTES = {
    "system_admin.process_role_expiries": {"queue": "default"},
}

BEAT_SCHEDULE = {
    "system_admin.process-role-expiries": {
        "task": "system_admin.process_role_expiries",
        "schedule": crontab(hour=0, minute=5),
        "options": {"expires": 3600},
    },
}
