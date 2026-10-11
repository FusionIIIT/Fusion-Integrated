"""Models for the Employee Leave Management (ELM) module."""
from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel


class LeaveType(TimeStampedModel):
    code = models.CharField(max_length=16, unique=True)
    name = models.CharField(max_length=80)
    annual_quota = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    can_carry_forward = models.BooleanField(default=False)
    requires_substitute = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "elm_leave_type"
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class LeaveBalance(TimeStampedModel, UserScopedModel):
    leave_type = models.ForeignKey(
        LeaveType, on_delete=models.PROTECT, related_name="balances"
    )
    year = models.PositiveIntegerField(default=2026)
    allocated = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    used = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    pending = models.DecimalField(max_digits=5, decimal_places=1, default=0)

    class Meta:
        db_table = "elm_leave_balance"
        ordering = ["leave_type__code"]
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "leave_type", "year"],
                name="elm_balance_user_type_year_uniq",
            )
        ]

    @property
    def remaining(self):
        return self.allocated - self.used - self.pending


class LeaveApplication(TimeStampedModel, UserScopedModel):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("recommended", "Recommended"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("withdrawn", "Withdrawn"),
        ("cancelled", "Cancelled"),
    ]

    leave_type = models.ForeignKey(
        LeaveType, on_delete=models.PROTECT, related_name="applications"
    )
    start_date = models.DateField()
    end_date = models.DateField()
    half_day = models.BooleanField(default=False)
    station_leave = models.BooleanField(default=False)
    station_address = models.CharField(max_length=255, blank=True)
    reason = models.TextField(blank=True)
    substitute_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    substitute_status = models.CharField(
        max_length=16, default="pending", blank=True
    )
    status = models.CharField(
        max_length=16, choices=STATUS_CHOICES, default="pending", db_index=True
    )
    reviewer_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    review_remarks = models.TextField(blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "elm_leave_application"
        ordering = ["-created_at"]

    @property
    def total_days(self):
        days = (self.end_date - self.start_date).days + 1
        return 0.5 if self.half_day and days == 1 else days


class HolidayCalendar(TimeStampedModel):
    date = models.DateField(unique=True)
    title = models.CharField(max_length=120)
    is_restricted = models.BooleanField(default=False)

    class Meta:
        db_table = "elm_holiday_calendar"
        ordering = ["date"]

    def __str__(self) -> str:
        return f"{self.date}: {self.title}"
