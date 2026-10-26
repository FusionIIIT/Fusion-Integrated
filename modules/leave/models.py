# Database models for Employee Leave Management (ELM)
from decimal import Decimal

from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel
from modules.leave.domain.constants import (
    ALL_HALF_DAYS,
    ALL_LEAVE_TYPES,
    ALL_STATUSES,
    HALF_DAY_NONE,
    STATUS_PENDING,
)


class LeaveBalance(UserScopedModel, TimeStampedModel):
    """Annual leave entitlement and consumption for an employee."""

    leave_type = models.CharField(
        max_length=10,
        choices=[(lt, lt) for lt in ALL_LEAVE_TYPES],
    )
    year = models.IntegerField()
    allocated = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    used = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "leave_type", "year"],
                name="unique_user_leave_year",
            )
        ]
        indexes = [
            models.Index(fields=["user_id", "year"], name="leave_bal_user_year_idx"),
        ]

    @property
    def available(self) -> Decimal:
        return self.allocated - self.used

    def __str__(self) -> str:
        return f"User {self.user_id} - {self.leave_type} ({self.year}): {self.available} left"


class LeaveApplication(UserScopedModel, TimeStampedModel):
    """Individual leave application request and approval record."""

    leave_type = models.CharField(
        max_length=10,
        choices=[(lt, lt) for lt in ALL_LEAVE_TYPES],
    )
    start_date = models.DateField()
    end_date = models.DateField()
    half_day = models.CharField(
        max_length=15,
        choices=[(hd, hd) for hd in ALL_HALF_DAYS],
        default=HALF_DAY_NONE,
    )
    days = models.DecimalField(max_digits=5, decimal_places=2)
    reason = models.TextField()
    is_station_leave = models.BooleanField(default=False)
    station_leave_address = models.TextField(blank=True)
    replacement_user_id = models.IntegerField(null=True, blank=True)
    status = models.CharField(
        max_length=15,
        choices=[(st, st) for st in ALL_STATUSES],
        default=STATUS_PENDING,
    )
    reviewed_by = models.IntegerField(null=True, blank=True)
    review_remarks = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["user_id", "status"], name="leave_app_user_status_idx"),
            models.Index(fields=["start_date", "end_date"], name="leave_app_dates_idx"),
        ]

    def __str__(self) -> str:
        return f"Application #{self.id} by User {self.user_id} ({self.leave_type}: {self.status})"
