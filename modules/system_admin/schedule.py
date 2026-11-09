"""Celery Beat crontab schedule and task queue routes for system_admin."""
from celery.schedules import crontab

TASK_ROUTES = {
    "system_admin.deliver_notifications": {"queue": "notifications"},
    "system_admin.sweep_scheduled_role_activations": {"queue": "maintenance"},
    "system_admin.sweep_expired_roles": {"queue": "maintenance"},
    "system_admin.send_role_expiry_reminders": {"queue": "maintenance"},
    "system_admin.sweep_expired_archived_user_windows": {"queue": "maintenance"},
    "system_admin.terminate_inactive_admin_sessions": {"queue": "security"},
}

BEAT_SCHEDULE = {
    # Outbox drainer: runs every 60 seconds (1-hour notification SLA, BR-SA-023)
    "system_admin.deliver-notifications": {
        "task": "system_admin.deliver_notifications",
        "schedule": 60.0,
        "options": {"expires": 55},
    },
    # Inactivity session sweep: runs every 5 minutes
    "system_admin.terminate-inactive-sessions": {
        "task": "system_admin.terminate_inactive_admin_sessions",
        "schedule": 300.0,
        "options": {"expires": 280},
    },
    # Role activation: runs every 10 minutes (BW-SA-04, UC-SA-028)
    "system_admin.sweep-scheduled-role-activations": {
        "task": "system_admin.sweep_scheduled_role_activations",
        "schedule": 600.0,
        "options": {"expires": 580},
    },
    # Role expiry: runs every 10 minutes (BW-SA-03, BW-SA-05, UC-SA-029)
    "system_admin.sweep-expired-roles": {
        "task": "system_admin.sweep_expired_roles",
        "schedule": 600.0,
        "options": {"expires": 580},
    },
    # Archived user reversible window finalization: runs hourly (BW-SA-08, UC-SA-031, ISS-SA-004)
    "system_admin.sweep-expired-archived-windows": {
        "task": "system_admin.sweep_expired_archived_user_windows",
        "schedule": crontab(minute=0),
        "options": {"expires": 3500},
    },
    # Role expiry reminders: runs daily at 07:00 AM (BR-SA-016, UC-SA-030)
    "system_admin.send-role-expiry-reminders": {
        "task": "system_admin.send_role_expiry_reminders",
        "schedule": crontab(hour=7, minute=0),
        "options": {"expires": 3600},
    },
}
