from __future__ import annotations

from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel


class LeaveType(models.TextChoices):
    CL = "CL", "Casual Leave"
    RH = "RH", "Restricted Holiday"
    SCL = "SCL", "Special Casual Leave"
    EL = "EL", "Earned Leave"
    COL = "COL", "Compensatory / Medical Leave"
    VL = "VL", "Vacation Leave"


class LeaveRequestStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    PENDING = "pending", "Pending"
    RECOMMENDED = "recommended", "Recommended"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    WITHDRAWN = "withdrawn", "Withdrawn"
    CANCEL_REQUESTED = "cancel_requested", "Cancel requested"
    CANCELLED = "cancelled", "Cancelled"


class LeaveRequest(TimeStampedModel, UserScopedModel):
    """A single leave application recorded in the ELM workflow."""

    leave_type = models.CharField(max_length=8, choices=LeaveType.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    days_requested = models.DecimalField(max_digits=5, decimal_places=2, default=1)
    purpose = models.TextField(blank=True)
    station_leave = models.BooleanField(default=False)
    station_leave_details = models.TextField(blank=True)
    is_half_day = models.BooleanField(default=False)
    half_day_period = models.CharField(max_length=16, blank=True)
    status = models.CharField(
        max_length=20,
        choices=LeaveRequestStatus.choices,
        default=LeaveRequestStatus.PENDING,
        db_index=True,
    )
    substitute_user_id = models.IntegerField(null=True, blank=True)
    substitute_status = models.CharField(
        max_length=20,
        default="pending",
        choices=[
            ("pending", "Pending"),
            ("accepted", "Accepted"),
            ("declined", "Declined"),
        ],
    )
    approved_by = models.IntegerField(null=True, blank=True)
    decision_note = models.TextField(blank=True)

    class Meta:
        db_table = "leave_request"
        ordering = ["-start_date", "-created_at"]

    def __str__(self) -> str:
        return f"{self.user_id}: {self.leave_type} ({self.status})"


class LeaveBalance(TimeStampedModel, UserScopedModel):
    """Annual leave balance information used for dashboard and review."""

    leave_type = models.CharField(max_length=8, choices=LeaveType.choices)
    year = models.PositiveIntegerField(default=2025)
    entitled_days = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    used_days = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    carried_forward_days = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    class Meta:
        db_table = "leave_balance"
        unique_together = ("user_id", "leave_type", "year")

    @property
    def available_days(self) -> float:
        return float(self.entitled_days + self.carried_forward_days - self.used_days)

    def __str__(self) -> str:
        return f"{self.user_id}: {self.leave_type} = {self.available_days}"


class ApprovalAction(TimeStampedModel, UserScopedModel):
    """An audit trail for recommended/approved/rejected decisions."""

    leave_request = models.ForeignKey(
        LeaveRequest,
        on_delete=models.CASCADE,
        related_name="approval_actions",
    )
    actor_user_id = models.IntegerField()
    action = models.CharField(max_length=32)
    decision_level = models.CharField(max_length=50, blank=True)
    comments = models.TextField(blank=True)

    class Meta:
        db_table = "leave_approval_action"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.leave_request_id}::{self.action}"
