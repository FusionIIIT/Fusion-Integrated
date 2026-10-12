from __future__ import annotations

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel


class LeaveRequest(UserScopedModel, TimeStampedModel):
    """A single leave request raised by an employee."""

    LEAVE_TYPES = [
        ("CL", "Casual Leave"),
        ("RH", "Restricted Holiday"),
        ("SCL", "Special Casual Leave"),
        ("EL", "Earned Leave"),
        ("COL", "Compensatory Off Leave"),
        ("VL", "Vacation Leave"),
    ]

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("cancelled", "Cancelled"),
    ]

    user_id = models.IntegerField(db_index=True)
    leave_type = models.CharField(max_length=8, choices=LEAVE_TYPES)
    start_date = models.DateField()
    end_date = models.DateField()
    days_requested = models.DecimalField(
        max_digits=4,
        decimal_places=1,
        default=Decimal("1.0"),
        validators=[MinValueValidator(Decimal("0.5"))],
    )
    half_day = models.BooleanField(default=False)
    reason = models.TextField(blank=True)
    substitute_user_id = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES,
                             default="pending")
    remarks = models.TextField(blank=True)

    class Meta:
        db_table = "elm_leave_request"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.user_id}:{self.leave_type}:{self.status}"


class LeaveBalance(UserScopedModel, TimeStampedModel):
    """Computed current entitlement snapshot for this user and leave type."""

    leave_type = models.CharField(max_length=8)
    year = models.CharField(max_length=8)
    entitled_days = models.DecimalField(max_digits=6, decimal_places=1, default=0)
    used_days = models.DecimalField(max_digits=6, decimal_places=1, default=0)
    remaining_days = models.DecimalField(max_digits=6, decimal_places=1, default=0)

    class Meta:
        db_table = "elm_leave_balance"
        unique_together = ("user_id", "leave_type", "year")

    def __str__(self) -> str:
        return f"{self.user_id}:{self.leave_type}:{self.year}"


class LeaveEvent(models.Model):
    """Audit trail for state transitions in the leave lifecycle."""

    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE,
                               related_name="events")
    actor_user_id = models.IntegerField()
    action = models.CharField(max_length=32)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "elm_leave_event"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.request_id}:{self.action}"
