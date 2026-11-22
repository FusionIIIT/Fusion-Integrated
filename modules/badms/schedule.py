"""BADMS-owned Celery schedule and worker routing."""
from celery.schedules import crontab

TASK_ROUTES = {
    "badms.dispatch_scheduled_backups": {"queue": "backups"},
    "badms.run_backup": {"queue": "backups"},
    "badms.deliver_notifications": {"queue": "notifications"},
    "badms.monitor_storage": {"queue": "reports"},
}

BEAT_SCHEDULE = {
    "badms.dispatch-scheduled-backups": {
        "task": "badms.dispatch_scheduled_backups",
        "schedule": crontab(minute="*"),
        "options": {"expires": 55},
    },
    "badms.deliver-notifications": {
        "task": "badms.deliver_notifications",
        "schedule": 60.0,
        "options": {"expires": 55},
    },
    "badms.monitor-storage": {
        "task": "badms.monitor_storage",
        "schedule": 900.0,
        "options": {"expires": 890},
    },
}
