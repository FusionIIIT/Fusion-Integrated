"""Timers this module owns. config/celery.py merges them; nothing is imported from here."""

from celery.schedules import crontab

TASK_ROUTES = {
    "oap.deliver_notifications": {"queue": "notifications"},
    "oap.send_pending_reminders": {"queue": "notifications"},
}

BEAT_SCHEDULE = {
    "oap.deliver-notifications": {
        "task": "oap.deliver_notifications",
        "schedule": 60.0,
        "options": {"expires": 55},
    },
    "oap.send-pending-reminders": {
        "task": "oap.send_pending_reminders",
        "schedule": crontab(minute="0"),
        "options": {"expires": 3000},
    },
}
