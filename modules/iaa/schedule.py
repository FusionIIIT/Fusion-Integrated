"""What IAA needs run on a timer; tasks are named by string so config imports nothing else."""

TASK_ROUTES: dict = {}

BEAT_SCHEDULE = {
    # IAA-BR-401: an approver who never acts must not block an item forever.
    "iaa.escalate-overdue-approvals": {
        "task": "iaa.escalate_overdue_approvals",
        "schedule": 600.0,
        "options": {"expires": 590},
    },
}
