"""What leave needs run on a timer. Tasks are named by string here and imported
only in tasks.py, so config merges this without importing anything out of the
module."""
from celery.schedules import crontab

#: Which pool each task lands on; without this everything queues on default.
TASK_ROUTES = {
    "leave.deliver_notifications": {"queue": "notifications"},
    "leave.process_year_end": {"queue": "default"},
    # Reminders and escalations stay on default, so a busy report queue can never
    # delay someone finding out their leave request is stuck.
}

BEAT_SCHEDULE = {
    # Drains often; each pass is capped by NOTIFY_MAX_PER_RUN.
    "leave.deliver-notifications": {
        "task": "leave.deliver_notifications",
        "schedule": 60.0,
        "options": {"expires": 55},
    },
    # BR-EL-032/033: hourly is fine-grained enough for a working-day threshold and
    # cheap, because both passes are single indexed queries.
    "leave.send-sla-reminders": {
        "task": "leave.send_sla_reminders",
        "schedule": crontab(minute=7),
        "options": {"expires": 3300},
    },
    "leave.escalate-overdue-tasks": {
        "task": "leave.escalate_overdue_tasks",
        "schedule": crontab(minute=17),
        "options": {"expires": 3300},
    },
    # BR-EL-001: the year-end run belongs to the closing month. It is idempotent
    # per person, so a repeated December run credits nobody twice.
    "leave.process-year-end": {
        "task": "leave.process_year_end",
        "schedule": crontab(day_of_month="1", hour=2, minute=13),
        "options": {"expires": 7200},
    },
}