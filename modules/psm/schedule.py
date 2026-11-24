from celery.schedules import crontab

TASK_ROUTES = {
    "psm.deliver_notifications": {"queue": "notifications"},
    "psm.run_scheduled_reports": {"queue": "reports"},
    "psm.check_approval_slas": {"queue": "default"},
}

BEAT_SCHEDULE = {
    "psm.deliver-notifications": {
        "task": "psm.deliver_notifications",
        "schedule": 60.0,
        "options": {"expires": 55},
    },
    "psm.check-approval-slas": {
        "task": "psm.check_approval_slas",
        "schedule": crontab(minute="*/15"),
        "options": {"expires": 800},
    },
    "psm.run-scheduled-reports": {
        "task": "psm.run_scheduled_reports",
        "schedule": crontab(minute="*/15"),
        "options": {"expires": 800},
    },
}
