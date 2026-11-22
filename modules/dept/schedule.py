"""Celery beat schedules for the Department module."""

from celery.schedules import crontab

TASK_ROUTES = {
    "dept.evaluate_role_transitions": {"queue": "default"},
}

BEAT_SCHEDULE = {
    "dept.evaluate-role-transitions": {
        "task": "dept.evaluate_role_transitions",
        "schedule": crontab(minute=0),  # hourly
        "options": {"expires": 3500},
    },
}
