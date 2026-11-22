"""Immutable-intent audit, notification and transactional outbox records."""

from django.db import models


class AuditEvent(models.Model):
    event_key = models.CharField(max_length=120, unique=True)
    actor_user_id = models.IntegerField(null=True, blank=True)
    acting_designation = models.CharField(max_length=150, blank=True)
    subject_user_id = models.IntegerField(null=True, blank=True)
    action = models.CharField(max_length=100)
    resource_kind = models.CharField(max_length=70)
    resource_id = models.IntegerField()
    data = models.JSONField(default=dict)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "hreis_audit"
        indexes = [
            models.Index(
                fields=["resource_kind", "resource_id", "recorded_at"], name="hr_audit_resource_idx"
            ),
            models.Index(fields=["subject_user_id", "-recorded_at"], name="hr_audit_subject_idx"),
        ]

    def __str__(self) -> str:
        return f"HR audit {self.event_key}"


class OutboxEvent(models.Model):
    event_key = models.CharField(max_length=120, unique=True)
    event_type = models.CharField(max_length=80)
    payload = models.JSONField(default=dict)
    queued_at = models.DateTimeField(auto_now_add=True)
    dispatched_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "hreis_outbox"
        indexes = [
            models.Index(fields=["dispatched_at", "queued_at"], name="hr_outbox_pending_idx"),
        ]

    def __str__(self) -> str:
        return f"HR outbox {self.event_key}"


class Notification(models.Model):
    recipient_user_id = models.IntegerField()
    request = models.ForeignKey(
        "HRRequest", on_delete=models.PROTECT, null=True, blank=True, related_name="notifications"
    )
    event_key = models.CharField(max_length=120, unique=True)
    title = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "hreis_notification"
        indexes = [
            models.Index(
                fields=["recipient_user_id", "-created_at"], name="hr_notification_recipient_idx"
            ),
        ]

    def __str__(self) -> str:
        return f"HR notice {self.pk} for {self.recipient_user_id}"
