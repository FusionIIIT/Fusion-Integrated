"""Celery beat schedule and task routes for FTS."""

TASK_ROUTES = {
    "fts.dispatch_pending_notifications": {"queue": "notifications"},
    "fts.verify_audit_integrity": {"queue": "reports"},
}

BEAT_SCHEDULE = {
    "fts.dispatch-pending-notifications": {
        "task": "fts.dispatch_pending_notifications",
        "schedule": 60.0,
        "options": {"expires": 55},
    },
    "fts.verify-audit-integrity": {
        "task": "fts.verify_audit_integrity",
        "schedule": 3600.0,
        "options": {"expires": 3500},
    },
}
