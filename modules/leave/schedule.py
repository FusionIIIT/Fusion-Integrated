"""What this module needs run on a timer.

Tasks are named by string, not imported, so config assembles the schedule
without importing anything out of the module.

Nothing scheduled these before. Approved leave never started, so it stayed
cancellable after the employee had gone and could never be extended; it never
reached its end date, so resumption never opened and nothing ever closed; and
no reminder or escalation ever fired.
"""
from celery.schedules import crontab

TASK_ROUTES = {
    "leave.advance_lifecycle": {"queue": "default"},
    "leave.process_sla": {"queue": "notifications"},
}

BEAT_SCHEDULE = {
    # Just after midnight: these transitions are calendar days, not moments, so
    # running at the turn of the day is what makes "starts today" true all day.
    # It is idempotent, so the 06:15 pass covers a worker that was down at 00:05.
    "leave.advance-lifecycle": {
        "task": "leave.advance_lifecycle",
        "schedule": crontab(hour="0,6", minute="5"),
        "options": {"expires": 3600},
    },
    # Thresholds are in hours, so a quarter-hour cadence is ample; a clock
    # already reminded is not reminded again.
    "leave.process-sla": {
        "task": "leave.process_sla",
        "schedule": crontab(minute="*/15"),
        "options": {"expires": 800},
    },
}
