"""Scheduled background tasks for the LMS module."""

TASK_ROUTES = {
    "lms.release_scheduled_materials": {"queue": "default"},
    "lms.release_scheduled_assignments": {"queue": "default"},
}

BEAT_SCHEDULE = {
    # Check for scheduled materials whose release time has passed every 60 seconds (BW-LMS-01).
    "lms.release-scheduled-materials": {
        "task": "lms.release_scheduled_materials",
        "schedule": 60.0,
        "options": {"expires": 55},
    },
    # Check for scheduled assignments whose release time has passed every 60 seconds (BW-LMS-03).
    "lms.release-scheduled-assignments": {
        "task": "lms.release_scheduled_assignments",
        "schedule": 60.0,
        "options": {"expires": 55},
    },
}
