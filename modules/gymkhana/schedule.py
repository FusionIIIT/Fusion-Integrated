BEAT_SCHEDULE = {
    "gymkhana.deliver-notifications": {
        "task": "gymkhana.deliver_notifications",
        "schedule": 60.0,
    },
}

TASK_ROUTES = {
    "gymkhana.deliver_notifications": {"queue": "notifications"},
}
