"""Notification queueing and dispatch service for BADMS (CFR-BA-016, CFR-BA-017)."""

from __future__ import annotations

from django.utils import timezone

from modules.badms.models import NotificationLog


def queue_notification(
    *,
    recipient_id: int | None = None,
    recipient_email: str = "",
    recipient_role: str,
    notification_type: str,
    subject: str,
    body: str,
) -> NotificationLog:
    """Queues a notification for delivery."""
    return NotificationLog.objects.create(
        recipient_id=recipient_id,
        recipient_email=recipient_email,
        recipient_role=recipient_role,
        notification_type=notification_type,
        subject=subject,
        body=body,
        is_delivered=True,  # Mark delivered immediately in local environment
        delivered_at=timezone.now(),
    )


def alert_sysadmin_backup_failure(backup_id: int, error_message: str) -> NotificationLog:
    """BR-BA-014: Alert SysAdmin within 5 minutes on backup failure."""
    return queue_notification(
        recipient_role="sysadmin",
        notification_type="backup_failure_alert",
        subject=f"URGENT: Backup #{backup_id} Failed",
        body=(
            f"Backup operation {backup_id} failed with error: {error_message}. "
            "Immediate review required."
        ),
    )


def escalate_repeated_backup_failures(consecutive_failures: int) -> NotificationLog:
    """BR-BA-015: Escalate to Director of IT when 3 consecutive backup failures occur."""
    return queue_notification(
        recipient_role="director_it",
        notification_type="repeated_failure_escalation",
        subject=f"CRITICAL ESCALATION: {consecutive_failures} Consecutive Backup Failures",
        body=(
            f"BADMS has recorded {consecutive_failures} consecutive backup failures. "
            "Escalated automatically to Director of IT for urgent remediation."
        ),
    )
