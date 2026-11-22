"""Scheduled reminders for configured patent maintenance cycles."""

from datetime import date, timedelta

from modules.pms.models import MaintenanceCycle, PmsConfiguration, PmsNotification


def process_maintenance_reminders(today=None):
    """Queue idempotent reminders for active cycles on configured alert days."""
    today = today or date.today()
    config = PmsConfiguration.objects.filter(key="maintenance_alert_days").first()
    intervals = config.value if config else [30, 15, 5]
    reminders = 0
    cycles = MaintenanceCycle.objects.filter(
        status=MaintenanceCycle.Status.ACTIVE,
        due_date__gte=today,
        due_date__lte=today + timedelta(days=max(intervals or [0])),
    ).select_related("application")
    for cycle in cycles.iterator():
        days_remaining = (cycle.due_date - today).days
        if days_remaining not in intervals:
            continue
        recipient = cycle.application.assigned_attorney_user_id
        if recipient is None:
            continue
        _, created = PmsNotification.objects.get_or_create(
            dedupe_key=f"maintenance:{cycle.pk}:reminder:{days_remaining}",
            defaults={
                "recipient_user_id": recipient,
                "application": cycle.application,
                "event": "maintenance.reminder",
                "subject": "Patent maintenance fee reminder",
                "body": (
                    f"{cycle.jurisdiction} maintenance is due in {days_remaining} day(s), "
                    f"on {cycle.due_date}."
                ),
            },
        )
        reminders += int(created)
    return {"reminders_queued": reminders}
