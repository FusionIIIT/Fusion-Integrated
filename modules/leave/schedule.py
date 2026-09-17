"""What this module needs run on a timer."""
from celery.schedules import crontab

TASK_ROUTES = {
    "leave.advance_lifecycle": {"queue": "default"},
    "leave.process_sla": {"queue": "notifications"},
}

BEAT_SCHEDULE = {
    # Just after midnight: these are calendar days, not moments.
    "leave.advance-lifecycle": {
        "task": "leave.advance_lifecycle",
        "schedule": crontab(hour="0,6", minute="5"),
        "options": {"expires": 3600},
    },
    # Thresholds are in hours, so a quarter-hour cadence is ample.
    "leave.process-sla": {
        "task": "leave.process_sla",
        "schedule": crontab(minute="*/15"),
        "options": {"expires": 800},
    },
}
