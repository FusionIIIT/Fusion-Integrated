"""Daily date gate for the currently configured ELM year-end boundary."""
from celery.schedules import crontab

BEAT_SCHEDULE = {
    "leave-notification-outbox": {
        "task": "leave.deliver_notifications",
        "schedule": crontab(minute="*/5"),
    },
    "leave-configured-year-end": {
        "task": "leave.process_configured_year_end",
        "schedule": crontab(minute=10, hour=0),
    },
    "leave-sla-thresholds": {
        "task": "leave.process_sla_thresholds",
        "schedule": crontab(minute="*/15"),
    },
}
TASK_ROUTES = {"leave.process_configured_year_end": {"queue": "scheduled"}}
TASK_ROUTES["leave.deliver_notifications"] = {"queue": "notifications"}
TASK_ROUTES["leave.process_sla_thresholds"] = {"queue": "scheduled"}
