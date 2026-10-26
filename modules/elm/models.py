"""Minimal persisted domain for employee leave applications.

This MVP deliberately implements submission and self-service tracking only.
Entitlement calculation, approval routing, calendar applicability and balance
updates remain outside this model until their corresponding workflows exist.
"""
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q

from core.db.mixins import TimeStampedModel, UserScopedModel


class LeaveCategory(models.TextChoices):
    """The leave categories supported by the synchronized ELM specification."""

    CL = "CL", "Casual Leave"
    RH = "RH", "Restricted Holiday"
    SCL = "SCL", "Special Casual Leave"
    EL = "EL", "Earned Leave"
    COL = "COL", "Commuted Leave"
    VL = "VL", "Vacation Leave"


class LeaveApplication(TimeStampedModel, UserScopedModel):
    """A full-day leave request owned by an IAM user ID.

    Institute identities live in the external IAM; `user_id` is intentionally a
    plain integer, matching other Fusion modules. Submitted requests are
    immutable through this MVP's API and begin in `pending` state.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        WITHDRAWN = "withdrawn", "Withdrawn"

    leave_type = models.CharField(max_length=3, choices=LeaveCategory.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(max_length=2000)
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.PENDING, db_index=True
    )

    class Meta:
        db_table = "elm_leave_application"
        ordering = ("-id",)
        constraints = [
            models.CheckConstraint(
                condition=Q(start_date__lte=F("end_date")),
                name="elm_leave_dates_ordered",
            ),
        ]
        indexes = [
            models.Index(fields=("user_id", "status"), name="elm_app_user_status_idx"),
            models.Index(fields=("user_id", "-created_at"), name="elm_app_user_created_idx"),
        ]

    def clean(self):
        super().clean()
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError({"end_date": "End date cannot be before start date."})

    @property
    def days_requested(self) -> int:
        """Inclusive calendar-day duration; this MVP does not support half-days."""
        return (self.end_date - self.start_date).days + 1

    def __str__(self) -> str:
        return f"Leave #{self.pk} for user {self.user_id} ({self.status})"
