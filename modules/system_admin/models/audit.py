"""Immutable audit logs and user activity metadata models."""
from django.db import models

from modules.system_admin.constants import AuditAction, AuditResult


class SuperAdminAuditLog(models.Model):
    """CRITICAL COMPLIANCE TABLE: Retained permanently, strictly immutable (BR-SA-025, CFR-SA-017)."""

    id = models.BigAutoField(primary_key=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    actor_id = models.IntegerField(db_index=True)
    actor_username = models.CharField(max_length=64)
    action = models.CharField(max_length=48, choices=AuditAction.choices, db_index=True)
    target_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    target_role_code = models.CharField(max_length=64, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    result = models.CharField(max_length=16, choices=AuditResult.choices, default=AuditResult.SUCCESS)
    reason = models.TextField(blank=True)
    context_metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "system_admin_audit_log"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["actor_id", "-timestamp"]),
            models.Index(fields=["action", "-timestamp"]),
            models.Index(fields=["target_user_id", "-timestamp"]),
        ]

    def delete(self, *args, **kwargs):
        raise PermissionError("Audit log entries are permanent and strictly immutable.")

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise PermissionError("Existing audit log entries cannot be modified.")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"[{self.timestamp}] {self.actor_username} - {self.action} ({self.result})"


class UserActivityLog(models.Model):
    """Tracks user session and activity metadata."""

    id = models.BigAutoField(primary_key=True)
    user_id = models.IntegerField(db_index=True)
    activity_type = models.CharField(max_length=32, db_index=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    session_id = models.CharField(max_length=64, blank=True)
    activity_metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "system_admin_user_activity_log"
        ordering = ["-timestamp"]

    def __str__(self):
        return f"[{self.timestamp}] User {self.user_id} - {self.activity_type}"
