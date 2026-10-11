from django.db import models
from core.db.mixins import TimeStampedModel, UserScopedModel


class LeaveType(TimeStampedModel):
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=60)
    max_days_per_year = models.PositiveSmallIntegerField(default=12)
    requires_attachment = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "leave_type"

    def __str__(self):
        return f"{self.code} - {self.name}"


class LeaveBalance(TimeStampedModel, UserScopedModel):
    leave_type = models.ForeignKey(LeaveType, on_delete=models.PROTECT, related_name="balances")
    year = models.PositiveIntegerField(default=2026)
    allocated_days = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)
    used_days = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)

    class Meta:
        db_table = "leave_balance"
        constraints = [
            models.UniqueConstraint(fields=["user_id", "leave_type", "year"], name="unique_user_leave_balance_per_year")
        ]

    @property
    def remaining_days(self):
        return float(self.allocated_days) - float(self.used_days)

    def __str__(self):
        return f"User {self.user_id} - {self.leave_type.code}: {self.remaining_days} remaining"


class LeaveRequest(TimeStampedModel, UserScopedModel):
    STATUS_CHOICES = [
        ("pending", "Pending Approval"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("cancelled", "Cancelled"),
    ]

    leave_type = models.ForeignKey(LeaveType, on_delete=models.PROTECT, related_name="requests")
    start_date = models.DateField()
    end_date = models.DateField()
    duration_days = models.DecimalField(max_digits=5, decimal_places=1)
    reason = models.TextField()
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="pending")
    
    # Approver details (referenced by user_id to follow no-cross-module FK rule)
    approver_user_id = models.IntegerField(null=True, blank=True)
    rejection_reason = models.CharField(max_length=255, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "leave_request"
        indexes = [
            models.Index(fields=["user_id", "status"], name="leave_req_user_status_idx"),
            models.Index(fields=["approver_user_id", "status"], name="leave_req_appr_status_idx"),
        ]

    def __str__(self):
        return f"Leave #{self.pk} by User {self.user_id} ({self.status})"
