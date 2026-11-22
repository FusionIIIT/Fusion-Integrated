"""MMS-owned periodic work."""

BEAT_SCHEDULE = {
    "mms.apply-vacation-defaults": {
        "task": "mms.apply_vacation_defaults",
        "schedule": 60.0,
        "options": {"expires": 55},
    },
}

TASK_ROUTES = {}
