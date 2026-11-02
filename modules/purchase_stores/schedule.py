"""Scheduled work owned by Purchase and Stores Management."""

TASK_ROUTES = {"purchase_stores.generate_scheduled_reports": {"queue": "reports"}}

BEAT_SCHEDULE = {
    "purchase-stores.generate-scheduled-reports": {
        "task": "purchase_stores.generate_scheduled_reports",
        "schedule": 300.0,
        "options": {"expires": 290},
    },
}
