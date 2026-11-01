"""Celery beat schedules and task routes for System Admin module.

Enables automated background lifecycle transitions without manual intervention.
"""
from celery.schedules import crontab

TASK_ROUTES = {
    "system_admin.send_role_expiry_reminders": {"queue": "notifications"},
    "system_admin.cleanup_inactive_sessions": {"queue": "default"},
    "system_admin.activate_scheduled_roles": {"queue": "default"},
    "system_admin.expire_time_bound_roles": {"queue": "default"},
    "system_admin.finalize_expired_archived_users": {"queue": "default"},
}

BEAT_SCHEDULE = {
    # UC-SA-028 / BW-SA-04: Activate scheduled roles at start of day
    "system_admin.activate-scheduled-roles": {
        "task": "system_admin.activate_scheduled_roles",
        "schedule": crontab(minute=5, hour=0),
        "options": {"expires": 3600},
    },
    # UC-SA-029 / BW-SA-03..05: Expire overdue roles daily
    "system_admin.expire-time-bound-roles": {
        "task": "system_admin.expire_time_bound_roles",
        "schedule": crontab(minute=10, hour=0),
        "options": {"expires": 3600},
    },
    # UC-SA-030 / BR-SA-016: Send reminder notifications each morning
    "system_admin.send-role-expiry-reminders": {
        "task": "system_admin.send_role_expiry_reminders",
        "schedule": crontab(minute=0, hour=8),
        "options": {"expires": 7200},
    },
    # UC-SA-031 / BW-SA-08: Finalize non-restorable archived users
    "system_admin.finalize-archived-users": {
        "task": "system_admin.finalize_expired_archived_users",
        "schedule": crontab(minute=0, hour=1),
        "options": {"expires": 3600},
    },
    # UC-SA-034 / BR-SA-027: Session cleanup every 15 minutes
    "system_admin.cleanup-inactive-sessions": {
        "task": "system_admin.cleanup_inactive_sessions",
        "schedule": crontab(minute="*/15"),
        "options": {"expires": 800},
    },
}
