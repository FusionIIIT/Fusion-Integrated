"""Audit log for workflow transitions and actions."""
from __future__ import annotations

from django.db import models
from core.db.mixins import TimeStampedModel
from modules.leave.models.applications import LeaveApplication


class LeaveActionHistory(TimeStampedModel):
    """Immutable audit trail of actions taken on an application."""

    application = models.ForeignKey(
        LeaveApplication, on_delete=models.CASCADE, related_name="actions"
    )
    actor_user_id = models.IntegerField(db_index=True)
    actor_role = models.CharField(max_length=60, blank=True)
    action = models.CharField(max_length=40)
    remarks = models.TextField(blank=True)

    class Meta:
        db_table = "leave_action_history"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"action#{self.pk} app#{self.application_id} {self.action} by u{self.actor_user_id}"
