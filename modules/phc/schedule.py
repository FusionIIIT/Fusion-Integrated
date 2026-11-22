BEAT_SCHEDULE = {
    "phc.deliver-notifications": {
        "task": "phc.deliver_notifications",
        "schedule": 60.0,
        "options": {"expires": 55},
    },
}

TASK_ROUTES = {
    "phc.deliver_notifications": {"queue": "notifications"},
}
