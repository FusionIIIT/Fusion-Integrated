from celery.schedules import crontab

BEAT_SCHEDULE = {
    "leave-sla-thresholds": {
        "task": "leave.process_sla_thresholds",
        "schedule": crontab(minute="*/15"),
    },
    "leave-notification-delivery": {
        "task": "leave.deliver_notifications",
        "schedule": crontab(minute="*/2"),
    },
    "leave-year-end-processing": {
        "task": "leave.run_year_end_processing",
        "schedule": crontab(minute=0, hour=0, day_of_month=1, month_of_year=1),
    },
}

TASK_ROUTES = {
    "leave.process_sla_thresholds": {"queue": "default"},
    "leave.deliver_notifications": {"queue": "default"},
    "leave.run_year_end_processing": {"queue": "default"},
}
