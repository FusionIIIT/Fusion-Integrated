"""What IAA needs run on a timer (IAA-BR-401, IAA-UC-203)."""

TASK_ROUTES = {
    "iaa.escalate_overdue_approvals": {"queue": "default"},
}

BEAT_SCHEDULE = {
    "iaa.escalate-overdue-approvals": {
        "task": "iaa.escalate_overdue_approvals",
        "schedule": 3600.0,
        "options": {"expires": 3500},
    },
}
