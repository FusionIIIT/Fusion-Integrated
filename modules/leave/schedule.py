"""What this module needs run on a timer.

Tasks are named by string, not imported, so config assembles the schedule
without importing anything out of the module. All three have to be running in
production: without the outbox drain nobody is told anything, without the SLA
sweep no request is ever chased, and without year-end the balances stop
matching institute policy.
"""
from celery.schedules import crontab

#: Which worker pool each task lands on; without it everything queues on default.
TASK_ROUTES = {
    "leave.deliver_notifications": {"queue": "notifications"},
    "leave.run_sla_sweep": {"queue": "notifications"},
    "leave.run_year_end": {"queue": "reports"},
}

BEAT_SCHEDULE = {
    # Drains often; each pass is capped by NOTIFY_MAX_PER_RUN.
    "leave.deliver-notifications": {
        "task": "leave.deliver_notifications",
        "schedule": 60.0,
        "options": {"expires": 55},
    },
    # BR-EL-032/033 measure in hours, so a quarter-hourly sweep is enough.
    "leave.sla-sweep": {
        "task": "leave.run_sla_sweep",
        "schedule": crontab(minute="*/15"),
        "options": {"expires": 800},
    },
    # EL-UC-020: the boundary the configured year end is measured from.
    "leave.year-end": {
        "task": "leave.run_year_end",
        "schedule": crontab(minute=30, hour=0),
        "options": {"expires": 3600},
    },
}
