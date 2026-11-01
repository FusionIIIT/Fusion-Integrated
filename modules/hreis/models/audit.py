"""Audit log and Notification models (BR-HR-024, BR-HR-025, BR-HR-026)."""
from django.core.exceptions import PermissionDenied
from django.db import models


class HrAuditLog(models.Model):
    """Immutable audit trail of all HR-EIS transactions (BR-HR-025, AFR-087)."""

    actor_id = models.IntegerField(db_index=True)
    actor_username = models.CharField(max_length=150)
    actor_role = models.CharField(max_length=64)
    action = models.CharField(max_length=128)
    entity_type = models.CharField(max_length=64, db_index=True)
    entity_id = models.CharField(max_length=64, db_index=True)
    details = models.JSONField(default=dict)
    ip_address = models.CharField(max_length=45, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "hreis_audit_log"
        verbose_name = "HR Audit Log"
        verbose_name_plural = "HR Audit Logs"
        ordering = ["-timestamp"]

    def save(self, *args, **kwargs):
        if self.pk:
            raise PermissionDenied("HR-EIS audit logs are immutable and cannot be updated (BR-HR-025).")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionDenied("HR-EIS audit logs are immutable and cannot be deleted (BR-HR-025).")

    def __str__(self) -> str:
        return f"AuditLog(actor={self.actor_username}, action={self.action}, entity={self.entity_type}:{self.entity_id})"


class HrNotification(models.Model):
    """System notification for HR events and reminders (BR-HR-024)."""

    CATEGORY_CHOICES = [
        ("submission", "Submission"),
        ("approval", "Approval"),
        ("rejection", "Rejection"),
        ("forwarding", "Forwarding"),
        ("reminder", "Pending Action Reminder"),
        ("policy", "Policy Update"),
    ]

    user_id = models.IntegerField(db_index=True)
    title = models.CharField(max_length=255)
    message = models.TextField()
    category = models.CharField(max_length=64, choices=CATEGORY_CHOICES, default="submission")
    link = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "hreis_notification"
        verbose_name = "HR Notification"
        verbose_name_plural = "HR Notifications"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Notification(user={self.user_id}, cat={self.category}, title={self.title})"
