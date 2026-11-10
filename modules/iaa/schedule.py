from celery.schedules import crontab

BEAT_SCHEDULE = {
    "iaa.escalate-approvals": {
        "task": "iaa.escalate_approvals",
        "schedule": crontab(minute="*/5"),
        "options": {"expires": 240},
    }
}
TASK_ROUTES = {"iaa.escalate_approvals": {"queue": "notifications"}}
