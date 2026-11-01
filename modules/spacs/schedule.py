TASK_ROUTES = {
    "spacs.deliver_notifications": {"queue": "notifications"},
}

BEAT_SCHEDULE = {
    "spacs.deliver-notifications": {
        "task": "spacs.deliver_notifications",
        "schedule": 60.0,
        "options": {"expires": 55},
    },
}
