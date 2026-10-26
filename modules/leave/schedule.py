"""Leave's own timers, named by string so config merges them without importing the module."""
from celery.schedules import crontab

TASK_ROUTES = {
    "leave.deliver_notifications": {"queue": "notifications"},
}

BEAT_SCHEDULE = {
    # BR-EL-035: an assignment nobody hears about is a request that waits.
    "leave.deliver-notifications": {
        "task": "leave.deliver_notifications",
        "schedule": 60.0,
        "options": {"expires": 55},
    },
    # EL-UC-021: thresholds are hours, so a quarter-hour tick is precise enough.
    "leave.process-sla": {
        "task": "leave.process_sla",
        "schedule": crontab(minute="*/15"),
        "options": {"expires": 800},
    },
    # EL-UC-020: daily, so a missed night is caught up the next one.
    "leave.year-boundary": {
        "task": "leave.year_boundary",
        "schedule": crontab(hour=0, minute=30),
        "options": {"expires": 6 * 3600},
    },
}
