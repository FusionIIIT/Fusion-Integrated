from celery.schedules import crontab

TASK_ROUTES = {
    "badms.evaluate_and_dispatch_due_backups": {"queue": "default"},
    "badms.monitor_storage_thresholds": {"queue": "reports"},
    "badms.check_backup_failure_sla": {"queue": "notifications"},
    "badms.purge_expired_archives": {"queue": "default"},
}

BEAT_SCHEDULE = {
    "badms.evaluate-due-backups": {
        "task": "badms.evaluate_and_dispatch_due_backups",
        "schedule": crontab(minute="*"),
        "options": {"expires": 55},
    },
    "badms.check-backup-failure-sla": {
        "task": "badms.check_backup_failure_sla",
        "schedule": 60.0,
        "options": {"expires": 55},
    },
    "badms.monitor-storage-thresholds": {
        "task": "badms.monitor_storage_thresholds",
        "schedule": crontab(minute=0, hour="*/6"),
        "options": {"expires": 3600},
    },
    "badms.purge-expired-archives": {
        "task": "badms.purge_expired_archives",
        "schedule": crontab(minute=0, hour=3),
        "options": {"expires": 3600},
    },
}
