"""What this module needs run on a timer. Merged by config/celery.py.

Tasks are named by string, so config assembles the schedule without importing
the module's internals. If beat is not running: no no-show or overstay alert
is ever raised, reminders never go out, and the notification outbox only grows.
"""
from celery.schedules import crontab

TASK_ROUTES = {
    "visitor_hostel.deliver_notifications": {"queue": "notifications"},
}

BEAT_SCHEDULE = {
    "visitor_hostel.deliver-notifications": {
        "task": "visitor_hostel.deliver_notifications",
        "schedule": 60.0,
        "options": {"expires": 55},
    },
    # A quarter of an hour is as late as a Caretaker should learn of a no-show.
    "visitor_hostel.scan-stays": {
        "task": "visitor_hostel.scan_stays",
        "schedule": crontab(minute="*/15"),
        "options": {"expires": 800},
    },
    "visitor_hostel.send-stay-reminders": {
        "task": "visitor_hostel.send_stay_reminders",
        "schedule": crontab(hour=8, minute=0),
        "options": {"expires": 3000},
    },
    "visitor_hostel.close-lapsed-duty": {
        "task": "visitor_hostel.close_lapsed_duty",
        "schedule": crontab(minute="*/10"),
        "options": {"expires": 500},
    },
}
