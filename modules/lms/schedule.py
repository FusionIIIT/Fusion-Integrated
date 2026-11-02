"""Scheduled background tasks for the LMS module."""

TASK_ROUTES = {
    "lms.release_scheduled_materials": {"queue": "default"},
}

BEAT_SCHEDULE = {
    # Check for scheduled materials whose release time has passed every 60 seconds (BW-LMS-01).
    "lms.release-scheduled-materials": {
        "task": "lms.release_scheduled_materials",
        "schedule": 60.0,
        "options": {"expires": 55},
    },
}
