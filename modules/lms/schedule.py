TASK_ROUTES = {}

BEAT_SCHEDULE = {
    "lms.release-scheduled-content": {
        "task": "lms.release_scheduled_content",
        "schedule": 60.0,
        "options": {"expires": 55},
    },
}
