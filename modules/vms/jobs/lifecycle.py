"""Beat schedule and routes for lane E (tasks live in `jobs/notifications.py`)."""
from __future__ import annotations

TASK_ROUTES = {
    "vms.deliver_notifications": {"queue": "notifications"},
    # Reminders/expiry stay on the default queue so they never wait behind email.
}

BEAT_SCHEDULE = {
    "vms-deliver-notifications": {
        "task": "vms.deliver_notifications", "schedule": 60.0,
        "options": {"queue": "notifications"}},
    "vms-send-reminders": {"task": "vms.send_reminders", "schedule": 300.0},
    "vms-expire-pending": {"task": "vms.expire_pending", "schedule": 300.0},
}
