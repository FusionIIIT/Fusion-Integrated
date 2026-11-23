"""Scheduled timers and task routing for Gymkhana."""

BEAT_SCHEDULE = {
    "gymkhana-expire-polls-hourly": {
        "task": "gymkhana.expire_polls",
        "schedule": 3600.0,
        "options": {"expires": 3500},
    },
}

TASK_ROUTES = {
    "gymkhana.*": {"queue": "default"},
}
