from __future__ import annotations

BEAT_SCHEDULE = {
    "superadmin-expire-reversibility-window": {
        "task": "modules.superadmin.tasks.expire_reversibility_window_task",
        "schedule": 86400.0,
    },
    "superadmin-expire-purge-requests": {
        "task": "modules.superadmin.tasks.expire_pending_purge_requests_task",
        "schedule": 21600.0,
    },
    "superadmin-drain-notification-outbox": {
        "task": "modules.superadmin.tasks.drain_notification_outbox_task",
        "schedule": 120.0,
    },
}

TASK_ROUTES = {
    "modules.superadmin.tasks.*": {"queue": "superadmin"},
}
