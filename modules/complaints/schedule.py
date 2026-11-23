"""Periodic Celery schedule for Complaint Management System.

Tasks are referenced by string name so that the schedule configuration
can assemble without eagerly importing domain modules.
"""
from celery.schedules import crontab

TASK_ROUTES = {
    "complaints.check_and_escalate_sla_breaches": {"queue": "default"},
    "complaints.check_and_send_sla_reminders": {"queue": "notifications"},
}

BEAT_SCHEDULE = {
    # BR-CMS-029 / UC-CMS-022 / BW-CMS-08: Automatically escalate complaints on SLA breach
    "complaints.check-and-escalate-sla-breaches": {
        "task": "complaints.check_and_escalate_sla_breaches",
        "schedule": 300.0,
        "options": {"expires": 290},
    },
    # BR-CMS-028 / UC-CMS-021: Trigger pre-breach reminder when approaching SLA deadline
    "complaints.check-and-send-sla-reminders": {
        "task": "complaints.check_and_send_sla_reminders",
        "schedule": 900.0,
        "options": {"expires": 850},
    },
}
