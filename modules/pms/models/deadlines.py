"""Deadline monitoring, reminders, escalations, and system configuration."""

from django.db import models

from core.db.mixins import TimeStampedModel
from modules.pms.models.applications import PatentApplication


class DeadlineTracking(TimeStampedModel):
    """Tracks patent deadlines with 30, 15, and 5-day alerts (BR-PMS-097..104)."""

    application = models.ForeignKey(
        PatentApplication, on_delete=models.CASCADE, related_name="deadlines"
    )
    deadline_type = models.CharField(
        max_length=50, db_index=True
    )  # director_review, revision, office_action, maintenance
    due_date = models.DateTimeField(db_index=True)
    alert_30_sent = models.BooleanField(default=False)
    alert_15_sent = models.BooleanField(default=False)
    alert_5_sent = models.BooleanField(default=False)
    is_escalated = models.BooleanField(default=False)
    escalated_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "pms_deadline_tracking"
        ordering = ["due_date"]
        indexes = [
            models.Index(fields=["deadline_type", "due_date"]),
        ]

    def __str__(self) -> str:
        return f"{self.deadline_type} due {self.due_date} (App {self.application_id})"


class PmsConfiguration(TimeStampedModel):
    """Institutional configuration for PMS (budget thresholds, escalation paths, active admin)."""

    key = models.CharField(max_length=100, unique=True, db_index=True)
    value = models.CharField(max_length=500)
    description = models.TextField(blank=True)

    class Meta:
        db_table = "pms_configuration"
        ordering = ["key"]

    def __str__(self) -> str:
        return f"{self.key} = {self.value}"
