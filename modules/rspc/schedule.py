"""Celery beat schedule for RSPC."""

SCHEDULE = {
    "rspc-check-project-deadlines": {
        "task": "modules.rspc.tasks.check_project_deadlines",
        "schedule": 86400.0,  # Run daily
    },
}
