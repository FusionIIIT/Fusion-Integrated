"""Alerts, notifications, audit trail and offline sync runs."""
from django.db import models

from .base import AppendOnlyModel, choice_check


class Alert(models.Model):
    """Security/admin alert (VMS-CFR-014, 026, 027)."""

    class Kind(models.TextChoices):
        BLACKLIST_HIT = "blacklist_hit"
        ZONE_VIOLATION = "zone_violation"
        GATE_FAILURE = "gate_failure"
        SUSPICIOUS = "suspicious"
        MUSTER = "muster"

    class Severity(models.TextChoices):
        LOW = "low"
        MEDIUM = "medium"
        HIGH = "high"
        CRITICAL = "critical"

    class Status(models.TextChoices):
        OPEN = "open"
        HANDLED = "handled"

    kind = models.CharField(max_length=20, choices=Kind.choices)
    severity = models.CharField(max_length=10, choices=Severity.choices,
                                default=Severity.MEDIUM)
    ref_type = models.CharField(max_length=40, blank=True)
    ref_id = models.BigIntegerField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices,
                              default=Status.OPEN)
    handled_by_user_id = models.IntegerField(null=True, blank=True)
    handled_at = models.DateTimeField(null=True, blank=True)
    detail = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        pass

    Meta.constraints = [
        choice_check("kind", Kind, "vms_alert_kind_valid"),
        choice_check("severity", Severity, "vms_alert_severity_valid"),
        choice_check("status", Status, "vms_alert_status_valid"),
    ]

    def __str__(self) -> str:
        return f"Alert {self.pk} ({self.kind}, {self.status})"


class Notification(models.Model):
    """Queued message; lane E delivers it (VMS-CFR-028, 021)."""

    class Channel(models.TextChoices):
        EMAIL = "email"
        SMS = "sms"
        INAPP = "inapp"

    class Status(models.TextChoices):
        PENDING = "pending"
        SENT = "sent"
        FAILED = "failed"
        SKIPPED = "skipped"

    topic = models.CharField(max_length=60)
    dedupe_key = models.CharField(max_length=200, unique=True)
    recipient_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    recipient_visitor = models.ForeignKey(
        "vms.Visitor", null=True, blank=True, on_delete=models.PROTECT,
        related_name="notifications")
    channel = models.CharField(max_length=10, choices=Channel.choices)
    subject = models.CharField(max_length=200, blank=True)
    body = models.TextField(blank=True)
    status = models.CharField(max_length=10, choices=Status.choices,
                              default=Status.PENDING)
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.CharField(max_length=500, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["status", "created_at"],
                                name="vms_notif_status_created_idx")]

    Meta.constraints = [
        choice_check("channel", Channel, "vms_notif_channel_valid"),
        choice_check("status", Status, "vms_notif_status_valid"),
    ]

    def __str__(self) -> str:
        return f"Notification {self.pk} ({self.topic}, {self.status})"


class AuditLog(AppendOnlyModel):
    """Append-only record of every state change (VMS-CFR-005)."""
    actor_user_id = models.IntegerField(null=True, blank=True)
    actor_role = models.CharField(max_length=30, blank=True)
    action = models.CharField(max_length=80)
    entity_type = models.CharField(max_length=60)
    entity_id = models.CharField(max_length=40)
    detail = models.JSONField(default=dict, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["entity_type", "entity_id"],
                                name="vms_audit_entity_idx")]

    def __str__(self) -> str:
        return f"{self.action} {self.entity_type}:{self.entity_id}"


class OfflineSyncRun(models.Model):
    """One batch of offline gate events uploaded (VMS-CFR-025)."""
    gate = models.ForeignKey("vms.Gate", on_delete=models.PROTECT,
                             related_name="sync_runs")
    received_at = models.DateTimeField(auto_now_add=True)
    events_total = models.PositiveIntegerField(default=0)
    events_applied = models.PositiveIntegerField(default=0)
    events_conflicted = models.PositiveIntegerField(default=0)
    detail = models.JSONField(default=dict, blank=True)

    def __str__(self) -> str:
        return f"OfflineSyncRun {self.pk} (gate {self.gate_id})"
