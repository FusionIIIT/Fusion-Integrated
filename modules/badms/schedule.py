"""Celery Beat schedules and task routes for BADMS."""

from celery.schedules import crontab

TASK_ROUTES = {
    "badms.execute_scheduled_backups": {"queue": "backups"},
    "badms.monitor_storage_thresholds": {"queue": "default"},
    "badms.drain_notification_queue": {"queue": "notifications"},
}

BEAT_SCHEDULE = {
    # Check effective schedules every minute
    "badms.execute-scheduled-backups": {
        "task": "badms.execute_scheduled_backups",
        "schedule": 60.0,
        "options": {"expires": 50},
    },
    # Periodic storage quota sweep
    "badms.monitor-storage-thresholds": {
        "task": "badms.monitor_storage_thresholds",
        "schedule": crontab(minute="*/15"),
        "options": {"expires": 800},
    },
    # Drain notification queue
    "badms.drain-notifications": {
        "task": "badms.drain_notification_queue",
        "schedule": 30.0,
        "options": {"expires": 25},
    },
}
