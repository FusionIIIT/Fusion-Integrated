"""Celery beat schedule and task routes for RSPC."""

from __future__ import annotations

TASK_ROUTES = {
    "modules.rspc.tasks.*": {"queue": "rspc"},
}

BEAT_SCHEDULE = {
    "rspc-check-project-deadlines": {
        "task": "modules.rspc.tasks.check_project_deadlines",
        "schedule": 86400.0,  # Run daily
    },
}
