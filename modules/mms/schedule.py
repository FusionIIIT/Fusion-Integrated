"""What MMS needs run on a timer.

Tasks are named by string, not imported, so config assembles the schedule
without importing anything out of the module.

MMS has clock-driven behaviour: default rejection of undecided special-food
requests, default-No vacation responses, next-calendar-day deregistration
activation, monthly bill generation, vacation reminders and outbox delivery.
"""

from celery.schedules import crontab

#: Which worker pool each task lands on.
TASK_ROUTES = {
    "mms.deliver_notifications": {"queue": "notifications"},
    "mms.default_reject_special_food": {"queue": "default"},
    "mms.default_vacation_response": {"queue": "default"},
    "mms.activate_deregistration": {"queue": "default"},
    "mms.generate_monthly_bills": {"queue": "billing"},
    "mms.send_vacation_reminder": {"queue": "default"},
}

BEAT_SCHEDULE = {
    # Drains often; each pass is capped by NOTIFY_MAX_PER_RUN.
    "mms.deliver-notifications": {
        "task": "mms.deliver_notifications",
        "schedule": 60.0,
        "options": {"expires": 55},
    },
    # BR-MMS-029: institution-defined decision period (policy row). Cadence is
    # frequent enough that the decision window is never meaningfully missed.
    "mms.default-reject-special-food": {
        "task": "mms.default_reject_special_food",
        "schedule": 300.0,
        "options": {"expires": 290},
    },
    # BR-MMS-027: survey deadline polling; exact deadline is per-survey.
    "mms.default-vacation-response": {
        "task": "mms.default_vacation_response",
        "schedule": 300.0,
        "options": {"expires": 290},
    },
    # BR-MMS-013: next-calendar-day effect for approved deregistration.
    "mms.activate-deregistration": {
        "task": "mms.activate_deregistration",
        "schedule": crontab(hour=0, minute=5),
        "options": {"expires": 3540},
    },
    # BR-MMS-016: calendar-month billing event (day within month is policy).
    "mms.generate-monthly-bills": {
        "task": "mms.generate_monthly_bills",
        "schedule": crontab(hour=1, minute=0, day_of_month=1),
        "options": {"expires": 3540},
    },
    # BR-MMS-035 / PS 3.3.10: vacation reminders; cadence is institution-defined.
    "mms.send-vacation-reminder": {
        "task": "mms.send_vacation_reminder",
        "schedule": crontab(hour=9, minute=0),
        "options": {"expires": 3540},
    },
}
