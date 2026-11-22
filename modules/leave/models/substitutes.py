"""Substitute requests and responsibilities."""
from __future__ import annotations

from django.db import models
from core.db.mixins import TimeStampedModel
from modules.leave.models.applications import LeaveApplication


class SubstituteRequest(TimeStampedModel):
    """Nominated responsibility coverage during absence (BR-EL-014, BR-EL-015, EL-UC-002)."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("declined", "Declined"),
    ]

    application = models.ForeignKey(
        LeaveApplication, on_delete=models.CASCADE, related_name="substitute_requests"
    )
    substitute_user_id = models.IntegerField(db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    responsibilities = models.TextField(blank=True)
    response_remarks = models.TextField(blank=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    is_current = models.BooleanField(default=True)

    class Meta:
        db_table = "leave_substitute_request"
        indexes = [
            models.Index(fields=["substitute_user_id", "status"], name="leave_sub_user_status_idx"),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"sub#{self.pk} app#{self.application_id} to u{self.substitute_user_id} ({self.status})"
