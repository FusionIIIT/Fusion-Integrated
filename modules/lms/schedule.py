"""Celery beat schedule and task routes for LMS."""
BEAT_SCHEDULE = {
    "lms.release_scheduled_materials": {
        "task": "modules.lms.tasks.release_scheduled_materials_task",
        "schedule": 60.0,
    },
    "lms.release_scheduled_assignments": {
        "task": "modules.lms.tasks.release_scheduled_assignments_task",
        "schedule": 60.0,
    },
}
TASK_ROUTES = {
    "modules.lms.tasks.release_scheduled_materials_task": {"queue": "default"},
    "modules.lms.tasks.release_scheduled_assignments_task": {"queue": "default"},
}
