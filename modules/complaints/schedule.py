"""CMS periodic work using configurable generic policy defaults."""

TASK_ROUTES = {
    "complaints.deliver_notifications": {"queue": "notifications"},
    "complaints.process_sla": {"queue": "notifications"},
}

BEAT_SCHEDULE = {
    "complaints.deliver-notifications": {
        "task": "complaints.deliver_notifications",
        "schedule": 60.0,
        "options": {"expires": 55},
    },
    "complaints.process-sla": {
        "task": "complaints.process_sla",
        "schedule": 900.0,
        "options": {"expires": 840},
    },
}
