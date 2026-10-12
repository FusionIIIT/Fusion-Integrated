"""Leave Management data models.

A local projection of the leave system. Kept for joins (you cannot ORDER BY a
field that lives behind an HTTP call) and for resilience while IAM is briefly
down. A cache with a table, never a source of truth — nothing here is edited by
hand.
"""
from django.db import models

from core.db.mixins import TimeStampedModel


class LeaveCategory(models.Model):
    """Supported leave categories."""
    CODE_CHOICES = [
        ("CL", "Casual Leave"),
        ("RH", "Restricted Holiday"),
        ("SCL", "Special Casual Leave"),
        ("EL", "Earned Leave"),
        ("COL", "Commuted Leave"),
        ("VL", "Vacation Leave"),
    ]

    code = models.CharField(max_length=2, primary_key=True)
    label = models.CharField(max_length=64)
    description = models.TextField(blank=True)

    class Meta:
        db_table = "leave_categories"
        ordering = ["code"]

    def __str__(self) -> str:
        return self.label


class LeaveBalance(models.Model):
    """Employee leave balance tracking."""
    EMPLOYEE_KIND_CHOICES = [
        ("faculty", "Faculty"),
        ("staff", "Staff"),
        ("student", "Student"),
    ]

    employee_id = models.IntegerField(primary_key=True)  # IAM's id
    kind = models.CharField(max_length=16, choices=EMPLOYEE_KIND_CHOICES, db_index=True)
    leave_category = models.ForeignKey(
        LeaveCategory, on_delete=models.CASCADE, related_name="balances"
    )
    year = models.PositiveSmallIntegerField()
    available = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    used = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    carried_over = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    entitlement = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "leave_balances"
        ordering = ["kind", "leave_category", "year", "-created_at"]
        indexes = [
            models.Index(fields=["kind", "leave_category", "year"]),
        ]

    def __str__(self) -> str:
        return f"{self.employee_id} - {self.kind} - {self.leave_category.code} - {self.year}"


class LeaveRequest(models.Model):
    """Leave request application."""
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("cancelled", "Cancelled"),
        ("resumed", "Resumed"),
    ]

    REQUEST_TYPE_CHOICES = [
        ("initial", "Initial Request"),
        ("extension", "Extension Request"),
        ("resumption", "Resumption Request"),
    ]

    user_id = models.IntegerField(primary_key=True)  # IAM's id
    leave_category = models.ForeignKey(
        LeaveCategory, on_delete=models.CASCADE, related_name="requests"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")
    request_type = models.CharField(
        max_length=20, choices=REQUEST_TYPE_CHOICES, default="initial"
    )
    start_date = models.DateField()
    end_date = models.DateField()
    duration_days = models.PositiveIntegerField()
    reason = models.TextField()
    station_leave = models.BooleanField(default=False)
    approved_by = models.CharField(max_length=64, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.CharField(max_length=64, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    resumed_by = models.CharField(max_length=64, blank=True)
    resumed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "leave_requests"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user_id", "status"]),
            models.Index(fields=["leave_category", "status"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} - {self.leave_category.code} - {self.status}"


class LeaveRequestAudit(models.Model):
    """Append-only audit trail for leave requests."""
    request = models.ForeignKey(
        LeaveRequest, on_delete=models.CASCADE, related_name="audits"
    )
    action = models.CharField(max_length=64)
    previous_status = models.CharField(max_length=20, blank=True)
    new_status = models.CharField(max_length=20)
    actor = models.CharField(max_length=64)
    actor_type = models.CharField(max_length=32)
    timestamp = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "leave_request_audits"
        ordering = ["-timestamp"]

    def __str__(self) -> str:
        return f"{self.request.id} - {self.action} - {self.actor}"


class LeaveSanction(models.Model):
    """Sanctioning authority decision on leave request."""
    request = models.ForeignKey(
        LeaveRequest, on_delete=models.CASCADE, related_name="sanctions"
    )
    authority = models.CharField(max_length=64)  # e.g., "Unit Head", "Dean"
    authority_type = models.CharField(max_length=32)  # e.g., "Processing", "Sanctioning"
    decision = models.CharField(max_length=64)  # "Approved", "Rejected", "Pending"
    decision_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "leave_sanctions"
        ordering = ["-decision_at"]

    def __str__(self) -> str:
        return f"{self.request.id} - {self.authority} - {self.decision}"


class LeaveHolidayCalendar(models.Model):
    """Published holiday/RH calendar."""
    year = models.PositiveSmallIntegerField(unique=True)
    holidays = models.JSONField(default=list, blank=True)  # List of {date, description}
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "leave_holiday_calendars"
        ordering = ["year"]

    def __str__(self) -> str:
        return f"{self.year} Holiday Calendar"


class LeavePolicy(models.Model):
    """Leave policy configuration."""
    policy_name = models.CharField(max_length=128, unique=True)
    version = models.CharField(max_length=32, unique=True)
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    cl_entitlement = models.DecimalField(max_digits=6, decimal_places=2, default=8.00)
    rh_entitlement = models.DecimalField(max_digits=6, decimal_places=2, default=2.00)
    scl_entitlement = models.DecimalField(max_digits=6, decimal_places=2, default=15.00)
    el_carry_forward = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "leave_policies"
        ordering = ["-effective_from"]

    def __str__(self) -> str:
        return f"{self.policy_name} v{self.version}"
