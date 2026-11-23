"""What LMS needs run on a timer."""

from __future__ import annotations

from celery.schedules import crontab

TASK_ROUTES = {
    "lms.process_scheduled_content_release": {"queue": "default"},
}

BEAT_SCHEDULE = {
    "lms.process-scheduled-content-release": {
        "task": "lms.tasks.process_scheduled_content_release",
        "schedule": crontab(minute="*"),
        "options": {"expires": 55},
    },
}
