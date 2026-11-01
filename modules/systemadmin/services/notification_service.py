"""Notification Service for System Admin Control Plane.

Implements administrative, user lifecycle, and security alert notifications
conforming to BR-SA-023, BR-SA-024, BR-SA-032, and CFR-SA-019.
"""
from typing import Any
from django.utils import timezone
from modules.systemadmin.models.audit import AdminNotification, SecurityAlert


class NotificationService:
    @staticmethod
    def send_notification(
        recipient_username: str,
        title: str,
        message: str,
        category: str = "account",
        channel: str = "in_system",
        recipient_role: str = "",
    ) -> AdminNotification:
        """Create and dispatch a notification to a basic user or administrator."""
        # Simulated delivery (in production can dispatch email/sms/in-app)
        notification = AdminNotification.objects.create(
            recipient_username=recipient_username,
            recipient_role=recipient_role or "",
            title=title,
            message=message,
            category=category,
            channel=channel,
            status="delivered",
            is_read=False,
        )
        return notification

    @staticmethod
    def trigger_security_alert(
        alert_type: str,
        message: str,
        severity: str = "CRITICAL",
        target_username: str = "",
        source_ip: str | None = None,
        channels: list[str] | None = None,
    ) -> SecurityAlert:
        """Record and broadcast a critical security alert (BR-SA-024)."""
        dispatched_channels = channels or ["in_system", "email"]
        alert = SecurityAlert.objects.create(
            alert_type=alert_type,
            severity=severity,
            message=message,
            target_username=target_username or "",
            source_ip=source_ip,
            channels_dispatched=dispatched_channels,
            is_resolved=False,
        )
        # Notify Super Admin inbox as well
        NotificationService.send_notification(
            recipient_username="superadmin",
            title=f"SECURITY ALERT [{severity}]: {alert_type}",
            message=message,
            category="security_alert",
            channel="in_system",
            recipient_role="Super Admin",
        )
        return alert

    @staticmethod
    def get_notifications_for_user(username: str, unread_only: bool = False):
        """Fetch notifications for a given user."""
        qs = AdminNotification.objects.filter(recipient_username=username).order_by("-created_at")
        if unread_only:
            qs = qs.filter(is_read=False)
        return qs
