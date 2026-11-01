TASK_ROUTES = {
    "complaints.deliver_notifications": {"queue": "notifications"},
}

BEAT_SCHEDULE = {
    "complaints.deliver-notifications": {
        "task": "complaints.deliver_notifications",
        "schedule": 60.0,
        "options": {"expires": 55},
    },
}
