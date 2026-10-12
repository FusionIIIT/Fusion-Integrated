"""What this module needs run on a timer.

Tasks are named by string, not imported, so config assembles the schedule
without importing anything out of the module.

Year-end processing is intentionally absent: it is a once-a-boundary action,
not a poll, and running it twice would double-lapse every balance.
"""
from celery.schedules import crontab

#: Which worker pool each task lands on; without it everything queues on default.
TASK_ROUTES = {
    "elm.deliver_notifications": {"queue": "notifications"},
    "elm.process_sla": {"queue": "notifications"},
}

BEAT_SCHEDULE = {
    # Drains often; each pass is capped by NOTIFY_MAX_PER_RUN.
    "elm.deliver-notifications": {
        "task": "elm.deliver_notifications",
        "schedule": 60.0,
        "options": {"expires": 55},
    },
    # SLA deadlines are measured in hours, so hourly is plenty.
    "elm.process-sla": {
        "task": "elm.process_sla",
        "schedule": crontab(minute=5),
        "options": {"expires": 3000},
    },
}
