"""PMS's own timers; config/celery.py merges them so the module stays removable."""
from celery.schedules import crontab

TASK_ROUTES = {
    "pms.deliver_notifications": {"queue": "notifications"},
    "pms.run_scheduled_reports": {"queue": "reports"},
}

BEAT_SCHEDULE = {
    # PMS-AFR-192..204: every notice the spec requires leaves through this drain.
    "pms.deliver-notifications": {
        "task": "pms.deliver_notifications",
        "schedule": 60.0,
        "options": {"expires": 55},
    },
    # BR-PMS-038, 097..104: expiry, alerts and escalations; deadlines are dates, so hourly.
    "pms.process-deadlines": {
        "task": "pms.process_deadlines",
        "schedule": crontab(minute=5),
        "options": {"expires": 3000},
    },
    # BR-PMS-022: does nothing unless PCC_ADMIN switched automatic routing on.
    "pms.auto-route": {
        "task": "pms.auto_route_submissions",
        "schedule": 600.0,
        "options": {"expires": 540},
    },
    # PMS-AFR-188: saved weekly and monthly report definitions.
    "pms.run-scheduled-reports": {
        "task": "pms.run_scheduled_reports",
        "schedule": crontab(minute=0, hour=6),
        "options": {"expires": 3600},
    },
}
