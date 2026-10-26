
"""Core leave application model for Employee Leave Management."""

from django.core.validators import MinValueValidator
from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel


class LeaveApplication(TimeStampedModel, UserScopedModel):
    """A leave request submitted by an institute employee."""

    LEAVE_TYPES = [
        ("CL", "Casual Leave"),
        ("RH", "Restricted Holiday"),
        ("SCL", "Special Casual Leave"),
        ("EL", "Earned Leave"),
        ("COL", "Commuted Leave"),
        ("VL", "Vacation Leave"),
    ]

    STATUSES = [
        ("submitted", "Submitted"),
        ("pending_substitute", "Pending Substitute"),
        ("pending_unit_head", "Pending Unit Head"),
        ("pending_sanction", "Pending Sanction"),
        ("recommended", "Recommended"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("withdrawn", "Withdrawn"),
        ("cancelled", "Cancelled"),
    ]

    leave_type = models.CharField(max_length=3, choices=LEAVE_TYPES)

    HALF_DAY_PERIODS = [
        ("first_half", "First Half"),
        ("second_half", "Second Half"),
    ]

    half_day_period = models.CharField(
        max_length=11,
        choices=HALF_DAY_PERIODS,
        null=True,
        blank=True,
    )

    start_date = models.DateField()
    end_date = models.DateField()
    requested_days = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        validators=[MinValueValidator(0.5)],
    )
    reason = models.TextField()
    status = models.CharField(
        max_length=24,
        choices=STATUSES,
        default="submitted",
        db_index=True,
    )
    substitute_user_id = models.IntegerField(null=True, blank=True)
    decision_user_id = models.IntegerField(null=True, blank=True)
    decision_at = models.DateTimeField(null=True, blank=True)
    decision_note = models.TextField(blank=True)

    class Meta:
        db_table = "elm_leave_application"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["user_id", "status"],
                name="elm_app_user_status_idx",
            ),
            models.Index(
                fields=["start_date", "end_date"],
                name="elm_app_dates_idx",
            ),
        ]

    def clean(self):
        super().clean()
        if self.end_date and self.start_date and self.end_date < self.start_date:
            from django.core.exceptions import ValidationError
            raise ValidationError({
                "end_date": "End date cannot be earlier than start date."
            })

    def __str__(self):
        return (
            f"{self.leave_type} leave by user {self.user_id} "
            f"({self.start_date} to {self.end_date})"
        )
