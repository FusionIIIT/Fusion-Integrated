"""Beat entries and queue routing owned by PMS."""

from celery.schedules import crontab

TASK_ROUTES = {
    "pms.deliver_notifications": {"queue": "notifications"},
}

BEAT_SCHEDULE = {
    # Alert thresholds are date-based, so one local-time sweep per day is enough.
    "pms.monitor-deadlines": {
        "task": "pms.monitor_deadlines",
        "schedule": crontab(minute=0, hour=6),
        "options": {"expires": 86100},
    },
    # Service-generated outbox rows are delivered promptly and retried next pass.
    "pms.deliver-notifications": {
        "task": "pms.deliver_notifications",
        "schedule": 60.0,
        "options": {"expires": 55},
    },
}
