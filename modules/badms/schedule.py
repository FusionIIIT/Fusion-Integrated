"""Celery beat schedules and task routes for BADMS.

Defines periodic tasks for autonomous backup execution and retention enforcement.
"""

from celery.schedules import crontab

BEAT_SCHEDULE = {
    "badms-periodic-backup-execution": {
        "task": "modules.badms.tasks.execute_scheduled_backups_task",
        "schedule": crontab(hour=2, minute=0),  # Daily at 02:00 AM
    },
    "badms-daily-retention-enforcement": {
        "task": "modules.badms.tasks.enforce_retention_policies_task",
        "schedule": crontab(hour=4, minute=0),  # Daily at 04:00 AM
    },
}

TASK_ROUTES = {
    "modules.badms.tasks.*": {"queue": "badms"},
}
