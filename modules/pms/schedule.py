"""What this module needs run on a timer.

Tasks are named by string, not imported, so config assembles the schedule
without importing anything out of the module.
"""
from celery.schedules import crontab

TASK_ROUTES = {
    "pms.check_office_action_deadlines": {"queue": "notifications"},
    "pms.check_maintenance_renewals": {"queue": "reports"},
    "pms.rebuild_patent_analytics": {"queue": "reports"},
}

BEAT_SCHEDULE = {
    # Daily statutory deadline monitoring for FER and hearing notices
    "pms.daily-deadline-monitor": {
        "task": "pms.check_office_action_deadlines",
        "schedule": crontab(hour=6, minute=0),
        "options": {"expires": 3600},
    },
    # Weekly annuity maintenance audit for granted patents
    "pms.weekly-maintenance-audit": {
        "task": "pms.check_maintenance_renewals",
        "schedule": crontab(day_of_week=1, hour=7, minute=0),
        "options": {"expires": 7200},
    },
    # Nightly aggregate snapshot for PMS reporting
    "pms.nightly-stats-rebuild": {
        "task": "pms.rebuild_patent_analytics",
        "schedule": crontab(hour=2, minute=30),
        "options": {"expires": 7200},
    },
}
