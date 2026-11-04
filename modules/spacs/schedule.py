"""Celery beat schedule and task routes for SPACS.

Operational timings are configurable via settings and environment variables.
"""
from __future__ import annotations

from celery.schedules import crontab
from django.conf import settings

TASK_ROUTES = {
    "spacs.deliver_notifications": {"queue": "notifications"},
    "spacs.process_sla_reminders": {"queue": "default"},
    "spacs.process_renewal_reminders": {"queue": "default"},
}

_NOTIFY_INTERVAL = float(getattr(settings, "SPACS_NOTIFICATION_DRAIN_SECONDS", 60))
_SLA_INTERVAL = float(getattr(settings, "SPACS_SLA_CHECK_INTERVAL_SECONDS", 3600))
_RENEWAL_HOUR = int(getattr(settings, "SPACS_RENEWAL_CHECK_CRON_HOUR", 8))
_RENEWAL_MINUTE = int(getattr(settings, "SPACS_RENEWAL_CHECK_CRON_MINUTE", 0))

BEAT_SCHEDULE = {
    # Drains outbox regularly
    "spacs.deliver-notifications": {
        "task": "spacs.deliver_notifications",
        "schedule": _NOTIFY_INTERVAL,
        "options": {"expires": max(10, int(_NOTIFY_INTERVAL) - 5)},
    },
    # Periodically checks pending tasks against SLA stages (UC-SPACS-024)
    "spacs.process-sla-reminders": {
        "task": "spacs.process_sla_reminders",
        "schedule": _SLA_INTERVAL,
        "options": {"expires": max(60, int(_SLA_INTERVAL) - 30)},
    },
    # Daily renewal reminder sweep for open renewal windows (UC-SPACS-025)
    "spacs.process-renewal-reminders": {
        "task": "spacs.process_renewal_reminders",
        "schedule": crontab(hour=_RENEWAL_HOUR, minute=_RENEWAL_MINUTE),
        "options": {"expires": 3600},
    },
}
