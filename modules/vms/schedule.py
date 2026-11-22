"""VMS Celery Timers and Task Routes."""

from celery.schedules import crontab

TASK_ROUTES = {
    "vms.check_overstays": {"queue": "default"},
    "vms.expire_stale_visits": {"queue": "default"},
}

BEAT_SCHEDULE = {
    "vms.check-overstays": {
        "task": "vms.check_overstays",
        "schedule": 600.0,
        "options": {"expires": 580},
    },
    "vms.expire-stale-visits": {
        "task": "vms.expire_stale_visits",
        "schedule": crontab(hour=0, minute=0),
        "options": {"expires": 3600},
    },
}
