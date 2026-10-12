"""What this module needs run on a timer.

Tasks are named by string, not imported, so config assembles the schedule
without importing anything out of the module.
"""
from celery.schedules import crontab

#: Which worker pool each task lands on; without it everything queues on default.
TASK_ROUTES = {
    "leave.sweep_sla": {"queue": "notifications"},
}

BEAT_SCHEDULE = {
    # BR-EL-032/033: pending files are reminded and escalated on the clock.
    "leave.sweep-sla": {
        "task": "leave.sweep_sla",
        "schedule": 900.0,          # 15 minutes
        "options": {"expires": 840},
    },
    # The boundary only bites once a year, but it must not be missed:
    # checked daily and a no-op once the year's marker row exists.
    "leave.year-end": {
        "task": "leave.run_year_end",
        "schedule": crontab(hour=1, minute=0),
        "options": {"expires": 21600},
    },
}
