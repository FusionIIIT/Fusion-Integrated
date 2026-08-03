"""What this module needs run on a timer.

Tasks are named by string, not imported, so config assembles the schedule
without importing anything out of the module.

Nothing scheduled these before, which meant `expire_overdue_offers` never ran:
an offer nobody answered stayed `issued` forever and kept its student blocked
from the pool, with no way out but a manual database edit.
"""
from celery.schedules import crontab

#: Which worker pool each task lands on. Without routing everything queues on
#: `default`, and the per-queue concurrency the deployment sets up does nothing.
TASK_ROUTES = {
    "placement.deliver_notifications": {"queue": "notifications"},
    "placement.rebuild_active_stats": {"queue": "reports"},
    "placement.rebuild_stats": {"queue": "reports"},
    # Offer expiry stays on `default`: it is short, transactional, and a
    # student waiting on it should not queue behind a report.
}

BEAT_SCHEDULE = {
    # The outbox is the only thing between a business write and an email, so
    # it drains often. Each pass is capped by NOTIFY_MAX_PER_RUN.
    "placement.deliver-notifications": {
        "task": "placement.deliver_notifications",
        "schedule": 60.0,
        "options": {"expires": 55},
    },
    # PC-BR-013. Five minutes is the resolution a student experiences as
    # "the deadline passed", and the sweep is cheap when nothing is due.
    "placement.expire-overdue-offers": {
        "task": "placement.expire_overdue_offers",
        "schedule": 300.0,
        "options": {"expires": 290},
    },
    # Snapshots back the student-facing stats page, so it never reads the
    # transactional tables.
    "placement.rebuild-active-stats": {
        "task": "placement.rebuild_active_stats",
        "schedule": crontab(minute="*/15"),
        "options": {"expires": 800},
    },
}
