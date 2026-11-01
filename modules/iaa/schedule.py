"""IAA-owned scheduled event evaluation."""
BEAT_SCHEDULE = {
    "iaa.escalate-overdue-approvals": {
        "task": "iaa.escalate_overdue_approvals",
        "schedule": 60.0,
        "options": {"expires": 55},
    },
    "iaa.process-automatic-anomalies": {
        "task": "iaa.process_automatic_anomalies",
        "schedule": 60.0,
        "options": {"expires": 55},
    },
}

TASK_ROUTES = {
    "iaa.escalate_overdue_approvals": {"queue": "default"},
    "iaa.process_automatic_anomalies": {"queue": "default"},
}
