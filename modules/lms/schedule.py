BEAT_SCHEDULE = {
    "lms-material-release": {"task": "modules.lms.tasks.release_due_materials", "schedule": 60.0},
    "lms-assignment-release": {
        "task": "modules.lms.tasks.release_due_assignments",
        "schedule": 60.0,
    },
}
TASK_ROUTES = {"modules.lms.tasks.*": {"queue": "celery"}}
