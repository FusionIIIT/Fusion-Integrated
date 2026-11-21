"""Audit records and internal durable outbox events."""

from uuid import uuid4

from django.db import models
from django.db.models import Q


class AuditEvent(models.Model):
    """Append-oriented event record with scalar aggregate and actor references."""

    event_id = models.UUIDField(default=uuid4, unique=True, editable=False)
    actor_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    actor_kind = models.CharField(max_length=32)
    action = models.CharField(max_length=80)
    aggregate_type = models.CharField(max_length=40)
    aggregate_id = models.PositiveBigIntegerField()
    result_status = models.CharField(max_length=20, blank=True)
    occurred_at = models.DateTimeField()
    context = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "quiz_audit_event"
        indexes = [
            models.Index(fields=["aggregate_type", "aggregate_id"], name="quiz_audit_aggregate_idx")
        ]

    def __str__(self) -> str:
        return f"{self.action} {self.aggregate_type}#{self.aggregate_id}"


class OutboxEvent(models.Model):
    """Versioned internal event awaiting a future, explicitly configured worker."""

    STATUS = [
        ("pending", "Pending"),
        ("claimed", "Claimed"),
        ("delivered", "Delivered"),
        ("dead", "Dead"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    event_type = models.CharField(max_length=128)
    schema_version = models.PositiveSmallIntegerField()
    aggregate_type = models.CharField(max_length=40)
    aggregate_id = models.PositiveBigIntegerField()
    dedupe_key = models.CharField(max_length=200)
    payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=12, choices=STATUS, default="pending")
    attempts = models.PositiveSmallIntegerField(default=0)
    available_at = models.DateTimeField(null=True, blank=True)
    lease_until = models.DateTimeField(null=True, blank=True)
    last_error_code = models.CharField(max_length=80, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "quiz_outbox_event"
        constraints = [
            models.UniqueConstraint(fields=["dedupe_key"], name="quiz_outbox_dedupe_key_uniq"),
        ]
        indexes = [
            models.Index(
                fields=["available_at"],
                condition=Q(status="pending"),
                name="quiz_outbox_pending_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.event_type} {self.aggregate_type}#{self.aggregate_id} ({self.status})"
