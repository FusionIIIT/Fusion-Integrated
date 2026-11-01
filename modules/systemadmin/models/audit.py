"""Audit Evidence, Session Monitoring, and Alert Models for System Admin Control Plane."""
from django.db import models
from core.db.mixins import TimeStampedModel


class SystemAdminAuditLog(models.Model):
    """Immutable audit trail for all System Admin actions (BR-SA-025, BR-SA-033).
    
    Audit logs cannot be modified or deleted and are retained permanently.
    """
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    actor_username = models.CharField(max_length=64, db_index=True)
    actor_role = models.CharField(max_length=64, default="Super Admin")
    action = models.CharField(max_length=64, db_index=True)
    target_user = models.CharField(max_length=64, blank=True, db_index=True)
    target_role = models.CharField(max_length=64, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    result = models.CharField(max_length=20, default="SUCCESS", db_index=True)  # SUCCESS, FAILURE, REJECTED
    reason_or_context = models.TextField(blank=True)
    metadata = models.JSONField(default=dict)

    class Meta:
        db_table = "systemadmin_audit_log"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["actor_username", "timestamp"], name="sa_audit_actor_time_idx"),
            models.Index(fields=["action", "timestamp"], name="sa_audit_action_time_idx"),
            models.Index(fields=["result", "timestamp"], name="sa_audit_result_time_idx"),
        ]

    def __str__(self) -> str:
        return f"[{self.timestamp}] {self.actor_username}: {self.action} ({self.result})"


class SessionLog(TimeStampedModel):
    session_id = models.CharField(max_length=128, unique=True, db_index=True)
    username = models.CharField(max_length=64, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    last_activity_at = models.DateTimeField(auto_now=True)
    terminated_at = models.DateTimeField(null=True, blank=True)
    termination_reason = models.CharField(max_length=32, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "systemadmin_session_log"
        ordering = ["-started_at"]

    def __str__(self) -> str:
        return f"Session {self.session_id} - {self.username} (Active: {self.is_active})"


class SecurityAlert(TimeStampedModel):
    SEVERITY_CHOICES = [
        ("INFO", "Info"),
        ("WARNING", "Warning"),
        ("CRITICAL", "Critical"),
    ]

    alert_type = models.CharField(max_length=64, db_index=True)
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default="WARNING")
    message = models.TextField()
    trigger_count = models.PositiveIntegerField(default=1)
    target_username = models.CharField(max_length=64, blank=True, db_index=True)
    source_ip = models.GenericIPAddressField(null=True, blank=True)
    channels_dispatched = models.JSONField(default=list)
    dispatched_at = models.DateTimeField(auto_now_add=True)
    is_resolved = models.BooleanField(default=False)

    class Meta:
        db_table = "systemadmin_security_alert"
        ordering = ["-dispatched_at"]

    def __str__(self) -> str:
        return f"Alert: {self.alert_type} [{self.severity}] - {self.message[:40]}"


class AdminNotification(TimeStampedModel):
    CATEGORY_CHOICES = [
        ("account", "Account Lifecycle"),
        ("role_lifecycle", "Role Lifecycle"),
        ("bulk_operation", "Bulk Operation"),
        ("archival", "Archival Lifecycle"),
        ("security_alert", "Security Alert"),
    ]

    recipient_username = models.CharField(max_length=64, db_index=True)
    recipient_role = models.CharField(max_length=64, blank=True)
    title = models.CharField(max_length=150)
    message = models.TextField()
    category = models.CharField(max_length=40, choices=CATEGORY_CHOICES, default="account")
    channel = models.CharField(max_length=20, default="in_system")  # in_system, email, sms
    status = models.CharField(max_length=20, default="delivered")  # delivered, pending, failed
    is_read = models.BooleanField(default=False)

    class Meta:
        db_table = "systemadmin_admin_notification"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Notification to {self.recipient_username}: {self.title}"
