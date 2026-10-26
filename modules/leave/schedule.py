BEAT_SCHEDULE = {
    "leave.process-sla": {
        "task": "leave.process_sla",
        "schedule": 3600.0,
        "options": {"expires": 3590},
    },
}

TASK_ROUTES = {
    "leave.process_sla": {"queue": "default"},
}
