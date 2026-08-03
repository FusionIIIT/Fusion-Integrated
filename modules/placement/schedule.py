"""What this module needs run on a timer.

Tasks are named by string, not imported, so config assembles the schedule
without importing anything out of the module.

Nothing scheduled these before, which meant `expire_overdue_offers` never ran:
an offer nobody answered stayed `issued` forever and kept its student blocked
from the pool, with no way out but a manual database edit.
"""
from celery.schedules import crontab

#: Which worker pool each task lands on; without it everything queues on default.
TASK_ROUTES = {
    "placement.deliver_notifications": {"queue": "notifications"},
    "placement.rebuild_active_stats": {"queue": "reports"},
    "placement.rebuild_stats": {"queue": "reports"},
    # Offer expiry stays on default so it never queues behind a report.
}

BEAT_SCHEDULE = {
    # Drains often; each pass is capped by NOTIFY_MAX_PER_RUN.
    "placement.deliver-notifications": {
        "task": "placement.deliver_notifications",
        "schedule": 60.0,
        "options": {"expires": 55},
    },
    # PC-BR-013: five minutes is what a student experiences as the deadline.
    "placement.expire-overdue-offers": {
        "task": "placement.expire_overdue_offers",
        "schedule": 300.0,
        "options": {"expires": 290},
    },
    # Snapshots back the stats page, so it never reads transactional tables.
    "placement.rebuild-active-stats": {
        "task": "placement.rebuild_active_stats",
        "schedule": crontab(minute="*/15"),
        "options": {"expires": 800},
    },
}
