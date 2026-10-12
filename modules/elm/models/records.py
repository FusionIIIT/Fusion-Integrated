"""Offline sanctions, notifications and SLA log."""
from django.db import models

from core.db.mixins import TimeStampedModel


class OfflineLeaveRecord(TimeStampedModel):
    """BR-EL-029: evidence of a sanction already made on paper."""

    request = models.OneToOneField("LeaveRequest", on_delete=models.PROTECT,
                                   related_name="offline_record")
    sanction_reference = models.CharField(max_length=120)
    sanctioned_by = models.CharField(max_length=120)
    sanctioned_on = models.DateField()
    evidence_note = models.CharField(max_length=500, blank=True)
    recorded_by_user_id = models.IntegerField()

    class Meta:
        db_table = "elm_offline_record"

    def __str__(self) -> str:
        return f"offline {self.sanction_reference}"


class Notification(models.Model):
    """In-app notice to one person or to whoever acts as a designation."""

    recipient_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    recipient_role = models.CharField(max_length=100, blank=True, db_index=True)
    request = models.ForeignKey("LeaveRequest", null=True, blank=True,
                                on_delete=models.CASCADE, related_name="notifications")
    message = models.CharField(max_length=400)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "elm_notification"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(recipient_user_id__isnull=False)
                | ~models.Q(recipient_role=""),
                name="elm_notification_has_recipient"),
        ]

    def __str__(self) -> str:
        return self.message[:40]


class SlaAction(models.Model):
    REMINDER = "reminder"
    ESCALATION = "escalation"

    request = models.ForeignKey("LeaveRequest", on_delete=models.CASCADE,
                                related_name="sla_actions")
    status = models.CharField(max_length=24)
    stage = models.PositiveSmallIntegerField()
    stage_entered_at = models.DateTimeField()
    action = models.CharField(max_length=12)
    target_role = models.CharField(max_length=100)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "elm_sla_action"
        constraints = [
            models.UniqueConstraint(
                fields=["request", "status", "stage", "stage_entered_at", "action"],
                name="elm_sla_once_per_stage"),
        ]

    def __str__(self) -> str:
        return f"{self.action} leave#{self.request_id}"
