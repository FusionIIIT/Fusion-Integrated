"""Celery beat schedules and routing for PMS."""

from celery.schedules import crontab

TASK_ROUTES = {
    "pms.evaluate_deadlines": {"queue": "notifications"},
    "pms.expire_overdue_revisions": {"queue": "default"},
}

BEAT_SCHEDULE = {
    # Run deadline evaluations every hour
    "pms.evaluate-deadlines": {
        "task": "pms.evaluate_deadlines",
        "schedule": 3600.0,
        "options": {"expires": 3500},
    },
    # Run 60-day revision expiration check every midnight
    "pms.expire-overdue-revisions": {
        "task": "pms.expire_overdue_revisions",
        "schedule": crontab(hour=0, minute=5),
        "options": {"expires": 86000},
    },
}
