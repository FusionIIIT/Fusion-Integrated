from celery.schedules import crontab

TASK_ROUTES = {
    "hr.deliver_notifications": {"queue": "notifications"},
    "hr.generate_pending_reminders": {"queue": "default"},
}

BEAT_SCHEDULE = {
    "hr.deliver-notifications": {
        "task": "hr.deliver_notifications",
        "schedule": 60.0,
        "options": {"expires": 55},
    },
    "hr.generate-pending-reminders": {
        "task": "hr.generate_pending_reminders",
        "schedule": crontab(minute=0),
        "options": {"expires": 3500},
    },
}
