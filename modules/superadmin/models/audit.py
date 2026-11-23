from __future__ import annotations

from django.db import models
from django.db.models import Index


class _ImmutableQuerySet(models.QuerySet):
    # Prevents bulk deletion of audit log entries at the QuerySet level
    def delete(self):
        raise PermissionError("Audit log entries are immutable and cannot be deleted.")


class _ImmutableManager(models.Manager):
    def get_queryset(self):
        return _ImmutableQuerySet(self.model, using=self._db)


class SuperAdminAuditLog(models.Model):
    id = models.BigAutoField(primary_key=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    actor_id = models.PositiveIntegerField(db_index=True)
    actor_username = models.CharField(max_length=150)
    actor_role = models.CharField(max_length=64)
    action = models.CharField(max_length=64, db_index=True)
    target_id = models.CharField(max_length=64, blank=True, db_index=True)
    target_type = models.CharField(max_length=64, blank=True)
    result = models.CharField(max_length=16, default="SUCCESS")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    reason = models.TextField(blank=True)
    context_metadata = models.JSONField(default=dict, blank=True)

    objects = _ImmutableManager()

    class Meta:
        db_table = "superadmin_audit_log"
        ordering = ["-timestamp"]
        indexes = [
            Index(fields=["actor_id", "-timestamp"], name="audit_actor_time_idx"),
            Index(fields=["action", "-timestamp"], name="audit_action_time_idx"),
            Index(fields=["target_type", "target_id", "-timestamp"], name="audit_target_time_idx"),
        ]

    def __str__(self) -> str:
        return f"[{self.timestamp}] {self.actor_username}: {self.action} ({self.result})"

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise PermissionError(
                "Audit log entries are immutable and cannot be modified after creation."
            )
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionError("Audit log entries are immutable and cannot be deleted.")


class UserActivityLog(models.Model):
    id = models.BigAutoField(primary_key=True)
    user_id = models.PositiveIntegerField(db_index=True)
    activity_type = models.CharField(max_length=64, db_index=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    session_id = models.CharField(max_length=128, blank=True)
    activity_metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "superadmin_user_activity_log"
        ordering = ["-timestamp"]

    def __str__(self) -> str:
        return f"[{self.timestamp}] User {self.user_id}: {self.activity_type}"
