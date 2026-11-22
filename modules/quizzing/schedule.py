"""Celery beat periodic task schedule for the Quizzing module."""

from celery.schedules import crontab

BEAT_SCHEDULE = {
    "quizzing.auto-submit-expired-attempts": {
        "task": "modules.quizzing.tasks.auto_submit_expired_attempts",
        "schedule": crontab(minute="*"),
    },
}

TASK_ROUTES = {
    "modules.quizzing.tasks.auto_submit_expired_attempts": {"queue": "default"},
}
