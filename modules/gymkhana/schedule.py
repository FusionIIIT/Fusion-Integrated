"""This module's timers; config/celery.py merges them by name."""

TASK_ROUTES = {
    "gymkhana.deliver_notifications": {"queue": "notifications"},
}

BEAT_SCHEDULE = {
    # AFR-GYM-013/015/025: without this no booking or poll notification is ever sent.
    "gymkhana.deliver-notifications": {
        "task": "gymkhana.deliver_notifications",
        "schedule": 60.0,
        "options": {"expires": 55},
    },
}
