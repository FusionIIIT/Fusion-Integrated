"""ELM scheduled work, merged by Fusion's Celery application."""
TASK_ROUTES = {
    "elm.process_sla_thresholds": {"queue": "notifications"},
    "elm.deliver_notifications": {"queue": "notifications"},
}

BEAT_SCHEDULE = {
    "elm.process-sla-thresholds": {
        "task": "elm.process_sla_thresholds",
        "schedule": 300.0,
        "options": {"expires": 290},
    },
    "elm.deliver-notifications": {
        "task": "elm.deliver_notifications",
        "schedule": 60.0,
        "options": {"expires": 55},
    },
}
