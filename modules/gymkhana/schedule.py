"""Scheduled timers and task routing for Gymkhana."""

BEAT_SCHEDULE = {
    "gymkhana-expire-polls-hourly": {
        "task": "gymkhana.expire_polls",
        "schedule": 3600.0,
        "options": {"expires": 3500},
    },
    "gymkhana-deliver-notifications": {
        "task": "gymkhana.deliver_notifications",
        "schedule": 60.0,
        "options": {"expires": 55},
    },
}

TASK_ROUTES = {
    "gymkhana.expire_polls": {"queue": "default"},
    "gymkhana.deliver_notifications": {"queue": "notifications"},
}
