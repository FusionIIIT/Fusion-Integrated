"""Scheduled work and Celery configuration for Hostel Management.
"""
from celery.schedules import crontab

BEAT_SCHEDULE = {
    "hostel.auto_expire_guest_bookings": {
        "task": "modules.hostel.tasks.auto_expire_guest_bookings",
        "schedule": crontab(hour=0, minute=0),
    },
}

TASK_ROUTES = {
    "modules.hostel.tasks.*": {"queue": "default"},
}
