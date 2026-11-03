from celery.schedules import crontab

BEAT_SCHEDULE = {
    "pms-deadlines": {"task": "pms.process_deadlines", "schedule": crontab(minute="*/15")},
    "pms-scan-documents": {"task": "pms.scan_documents", "schedule": crontab(minute="*/5")},
    "pms-deliver-notifications": {
        "task": "pms.deliver_notifications",
        "schedule": crontab(minute="*/5"),
    },
}
TASK_ROUTES = {"pms.*": {"queue": "default"}}
