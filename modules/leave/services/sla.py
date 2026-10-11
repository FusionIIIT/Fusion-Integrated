"""SLA processing service.

Implements EL-UC-021, EVT-02, BR-EL-032, BR-EL-033, BR-EL-035, BR-EL-038.
"""

from datetime import timedelta

from django.utils import timezone

from modules.leave.models.sla import SlaTaskClock, SlaThreshold


def process_sla_clocks() -> dict:
    """Checks all active pending SLA task clocks for reminder and escalation triggers."""
    now = timezone.now()
    thresholds = {t.task_type: t for t in SlaThreshold.objects.all()}

    pending_clocks = SlaTaskClock.objects.filter(is_pending=True)
    reminded_count = 0
    escalated_count = 0

    for clock in pending_clocks:
        config = thresholds.get(clock.task_type)
        rem_hours = config.reminder_hours if config else 24
        esc_hours = config.escalation_hours if config else 48

        age = now - clock.assigned_at

        # BR-EL-032: Check reminder threshold
        if age >= timedelta(hours=rem_hours) and clock.reminded_at is None:
            clock.reminded_at = now
            clock.save(update_fields=["reminded_at", "updated_at"])
            reminded_count += 1

        # BR-EL-033: Check escalation threshold
        if age >= timedelta(hours=esc_hours) and clock.escalated_at is None:
            clock.escalated_at = now
            clock.save(update_fields=["escalated_at", "updated_at"])
            escalated_count += 1

    return {
        "processed_at": now.isoformat(),
        "total_pending_clocks": pending_clocks.count(),
        "reminded_count": reminded_count,
        "escalated_count": escalated_count,
    }
