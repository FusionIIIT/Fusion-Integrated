"""What this module needs run on a timer.

Tasks are named by string, not imported, so config assembles the schedule
without importing anything out of the module.

Two entries correspond to the baseline's event triggers: EVT-01 (the configured
year-end boundary, EL-UC-020) and EVT-02 (a configured SLA threshold reached,
EL-UC-021). The year-end task is not on a fixed date — it is dispatched by the
sweep below on the day the *current* policy says the boundary falls, so moving
the boundary is a configuration change rather than a deploy.
"""
from celery.schedules import crontab

#: Which worker pool each task lands on; without it everything queues on default.
TASK_ROUTES = {
    "leave.deliver_notifications": {"queue": "notifications"},
}

BEAT_SCHEDULE = {
    # Drains often; each pass is capped by NOTIFY_MAX_PER_RUN.
    "leave.deliver-notifications": {
        "task": "leave.deliver_notifications",
        "schedule": 60.0,
        "options": {"expires": 55},
    },
    # EL-UC-021 / EVT-02: hourly is far finer than any configured threshold.
    "leave.process-sla": {
        "task": "leave.process_sla",
        "schedule": crontab(minute=7),
        "options": {"expires": 3500},
    },
    # EL-UC-020 / EVT-01: the boundary check runs early on the configured day.
    "leave.check-year-end-boundary": {
        "task": "leave.check_year_end_boundary",
        "schedule": crontab(minute=30, hour=1),
        "options": {"expires": 80000},
    },
}
