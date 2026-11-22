"""Hostel-owned scheduled work, assembled by the platform Celery configuration."""

BEAT_SCHEDULE = {
    "hostel-alerts": {
        "task": "visitor_hostel.generate_alerts",
        "schedule": 60.0,
        "options": {"expires": 55},
    },
    "hostel-notifications": {
        "task": "visitor_hostel.deliver_notifications",
        "schedule": 60.0,
        "options": {"expires": 55},
    },
}
TASK_ROUTES = {"visitor_hostel.deliver_notifications": {"queue": "notifications"}}
