from celery.schedules import crontab

BEAT_SCHEDULE = {
    "badms-run-due-schedules": {
        "task": "badms.run_due_schedules",
        "schedule": 60.0,
        "options": {"expires": 55},
    },
    "badms-deliver-notifications": {
        "task": "badms.deliver_notifications",
        "schedule": 60.0,
        "options": {"expires": 55},
    },
    "badms-monitor-storage-thresholds": {
        "task": "badms.monitor_storage_thresholds",
        "schedule": 300.0,
        "options": {"expires": 290},
    },
    "badms-enforce-retention": {
        "task": "badms.enforce_retention",
        "schedule": crontab(hour=3, minute=0),
        "options": {"expires": 3500},
    },
}

TASK_ROUTES = {
    "badms.execute_backup": {"queue": "default"},
    "badms.run_due_schedules": {"queue": "default"},
    "badms.deliver_notifications": {"queue": "notifications"},
    "badms.monitor_storage_thresholds": {"queue": "default"},
    "badms.enforce_retention": {"queue": "default"},
}
