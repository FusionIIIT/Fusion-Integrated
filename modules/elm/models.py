from __future__ import annotations

from datetime import date

from django.core.exceptions import ValidationError
from django.db import models

from core.db.mixins import TimeStampedModel


class LeaveCategory(models.TextChoices):
    CL = "CL", "Casual Leave"
    RH = "RH", "Restricted Holiday"
    SCL = "SCL", "Special Casual Leave"
    EL = "EL", "Encashable Leave"
    COL = "COL", "Compensatory Leave"
    VL = "VL", "Vacation Leave"


class LeaveStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    CANCELLED = "cancelled", "Cancelled"
    WITHDRAWN = "withdrawn", "Withdrawn"


class LeaveCategoryManager(models.Manager):
    def get_available_choices(self):
        return dict(LeaveCategory.choices)


class RoleBasedUnit(TimeStampedModel):
    """Simple unit grouping used for leave routing and approvals."""

    code = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="children",
    )

    class Meta:
        db_table = "elm_role_based_unit"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class LeavePolicy(TimeStampedModel):
    """Keep leave entitlements simple and explicit for a given period."""

    employee_type = models.CharField(
        max_length=24,
        default="all",
        choices=[
            ("all", "All employees"),
            ("staff", "Staff"),
            ("faculty", "Faculty"),
        ],
    )
    leave_type = models.CharField(max_length=16, choices=LeaveCategory.choices)
    annual_quota = models.PositiveSmallIntegerField(default=0)
    carry_forward_days = models.PositiveSmallIntegerField(default=0)
    encashment_allowed = models.BooleanField(default=False)
    min_service_days = models.PositiveIntegerField(default=0)
    effective_from = models.DateField(default=date.today)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "elm_leave_policy"
        ordering = ["leave_type", "effective_from"]
        unique_together = ["leave_type", "employee_type", "effective_from"]

    def __str__(self) -> str:
        return f"{self.get_leave_type_display()} ({self.employee_type})"


class HolidayCalendar(TimeStampedModel):
    """Public calendar dates that are excluded from leave eligibility."""

    holiday_name = models.CharField(max_length=120)
    holiday_date = models.DateField(unique=True)
    is_recurring = models.BooleanField(default=False)
    is_optional = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "elm_holiday_calendar"
        ordering = ["holiday_date"]

    def __str__(self) -> str:
        return self.holiday_name


class LeaveApplication(TimeStampedModel):
    """Single leave request from an employee to an approver."""

    employee_user_id = models.IntegerField(db_index=True)
    employee_name = models.CharField(max_length=120, blank=True)
    leave_type = models.CharField(max_length=16, choices=LeaveCategory.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(blank=True)
    is_half_day = models.BooleanField(default=False)
    status = models.CharField(
        max_length=16,
        choices=LeaveStatus.choices,
        default=LeaveStatus.PENDING,
    )
    unit = models.ForeignKey(
        RoleBasedUnit,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="leave_applications",
    )
    unit_head_id = models.IntegerField(null=True, blank=True)
    substitute_id = models.IntegerField(null=True, blank=True)
    comments = models.TextField(blank=True)
    created_by = models.IntegerField(default=0)
    last_action_by = models.IntegerField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "elm_leave_application"
        ordering = ["-created_at"]

    def clean(self):
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError({"end_date": "End date must be on or after start date."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    @property
    def duration_days(self) -> int:
        if not self.start_date or not self.end_date:
            return 0
        total_days = (self.end_date - self.start_date).days + 1
        return max(total_days, 1)

    def __str__(self) -> str:
        return f"{self.employee_name or self.employee_user_id} - {self.get_leave_type_display()}"
