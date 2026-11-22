TASK_ROUTES = {
    "vms.deliver_notifications": {"queue": "notifications"},
}
BEAT_SCHEDULE = {
    "vms.deliver-notifications": {
        "task": "vms.deliver_notifications",
        "schedule": 60.0,
        "options": {"expires": 55},
    },
    "vms.expire-overdue-visits": {
        "task": "vms.expire_overdue_visits",
        "schedule": 300.0,
        "options": {"expires": 290},
    },
    "vms.expire-passes": {
        "task": "vms.expire_visit_passes",
        "schedule": 300.0,
        "options": {"expires": 290},
    },
    "vms.auto-checkout": {
        "task": "vms.auto_checkout_visitors",
        "schedule": 300.0,
        "options": {"expires": 290},
    },
    "vms.reconcile-offline": {
        "task": "vms.reconcile_offline_entries",
        "schedule": 60.0,
        "options": {"expires": 55},
    },
    "vms.approval-reminders": {
        "task": "vms.queue_approval_reminders",
        "schedule": 300.0,
        "options": {"expires": 290},
    },
    "vms.scan-pending-documents": {
        "task": "vms.scan_pending_documents",
        "schedule": 60.0,
        "options": {"expires": 55},
    },
}
