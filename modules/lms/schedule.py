from celery.schedules import crontab

TASK_ROUTES = {
    "lms.publish_scheduled_content": {"queue": "default"},
}

BEAT_SCHEDULE = {
    "lms.publish-scheduled-content": {
        "task": "lms.publish_scheduled_content",
        "schedule": crontab(minute="*/5"),
        "options": {"expires": 290},
    },
}
