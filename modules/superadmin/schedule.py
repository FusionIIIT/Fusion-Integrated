"""Celery beat schedule and task routing for Super Admin."""

from celery.schedules import crontab

TASK_ROUTES = {
    "superadmin.finalize_archived_user_reversibility_expiry": {"queue": "periodic"},
    "superadmin.activate_scheduled_roles": {"queue": "periodic"},
    "superadmin.expire_time_bound_roles": {"queue": "periodic"},
    "superadmin.send_role_expiry_reminders": {"queue": "notifications"},
}

BEAT_SCHEDULE = {
    # BW-SA-08 Transition 2: sweeps expired reversibility windows hourly.
    "superadmin.finalize-archived-user-reversibility-expiry": {
        "task": "superadmin.finalize_archived_user_reversibility_expiry",
        "schedule": crontab(minute=0),
        "options": {"expires": 3500},
    },
    # BW-SA-04: activates scheduled role assignments.
    "superadmin.activate-scheduled-roles": {
        "task": "superadmin.activate_scheduled_roles",
        "schedule": crontab(minute="*/15"),
        "options": {"expires": 800},
    },
    # BW-SA-03: expires elapsed time-bound roles.
    "superadmin.expire-time-bound-roles": {
        "task": "superadmin.expire_time_bound_roles",
        "schedule": crontab(minute="*/15"),
        "options": {"expires": 800},
    },
}
