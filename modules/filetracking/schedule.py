"""Periodic beat schedule and routing for File Tracking System."""

BEAT_SCHEDULE = {
    "filetracking-reconcile-outbox": {
        "task": "modules.filetracking.tasks.reconcile_outbox_notifications",
        "schedule": 300.0,  # 5 minutes
        "options": {"expires": 240},
    },
    "filetracking-audit-integrity-check": {
        "task": "modules.filetracking.tasks.verify_audit_integrity",
        "schedule": 86400.0,  # 24 hours
        "options": {"expires": 80000},
    },
}

TASK_ROUTES = {
    "modules.filetracking.tasks.*": {"queue": "default"},
}
