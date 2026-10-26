
"""Database model for Employee Leave Management applications."""

import uuid

from django.db import models


class LeaveApplication(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        PENDING_APPROVAL = "pending_approval", "Pending Approval"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        WITHDRAWN = "withdrawn", "Withdrawn"
        CANCELLED = "cancelled", "Cancelled"
        EXTENSION_REQUESTED = "extension_requested", "Extension Requested"
        RESUMED = "resumed", "Resumed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    employee_id = models.CharField(max_length=128, db_index=True)
    leave_type = models.CharField(max_length=32)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    start_half = models.CharField(max_length=8, blank=True, default="")
    end_half = models.CharField(max_length=8, blank=True, default="")
    requested_days = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )

    approver_id = models.CharField(max_length=128, blank=True, default="")
    decision_note = models.TextField(blank=True, default="")
    submitted_at = models.DateTimeField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "elm"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["employee_id", "status"],
                name="elm_emp_status_idx",
            ),
            models.Index(
                fields=["start_date", "end_date"],
                name="elm_leave_dates_idx",
            ),
        ]

    def __str__(self):
        return (
            f"{self.employee_id}: {self.leave_type} "
            f"({self.start_date} to {self.end_date})"
        )
