"""SLA threshold and tracking clock models.

Implements SLA configuration and pending task clocks (EL-UC-018, EL-UC-021 / BR-EL-032, BR-EL-033, BR-EL-038).
"""
from django.db import models

from core.db.mixins import TimeStampedModel
from modules.leave.models.extensions import LeaveExtension
from modules.leave.models.requests import LeaveRequest


class SlaThreshold(TimeStampedModel):
    task_type = models.CharField(max_length=50, unique=True)
    reminder_hours = models.IntegerField(default=24)
    escalation_hours = models.IntegerField(default=48)
    escalation_action = models.CharField(max_length=50, default="notify")

    class Meta:
        ordering = ["task_type"]


class SlaTaskClock(TimeStampedModel):
    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE, related_name="sla_clocks")
    extension = models.ForeignKey(
        LeaveExtension,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="sla_clocks",
    )
    task_type = models.CharField(max_length=50)
    assigned_to_user_id = models.IntegerField(null=True, blank=True)
    assigned_to_role = models.CharField(max_length=50)
    state = models.CharField(max_length=50)
    assigned_at = models.DateTimeField(auto_now_add=True)
    reminded_at = models.DateTimeField(null=True, blank=True)
    escalated_at = models.DateTimeField(null=True, blank=True)
    is_pending = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["-assigned_at"]
