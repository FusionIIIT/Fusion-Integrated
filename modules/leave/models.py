from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel


class LeaveType(TimeStampedModel):
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=60)
    max_days_per_year = models.PositiveSmallIntegerField(default=12)
    requires_attachment = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    # Entitlement / treatment flags (ELM v1.4)
    carry_forward = models.BooleanField(default=False)
    continuous_count = models.BooleanField(default=False)
    allow_half_day = models.BooleanField(default=False)
    requires_rh_calendar = models.BooleanField(default=False)
    requires_vacation_period = models.BooleanField(default=False)

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
            models.UniqueConstraint(
                fields=["user_id", "leave_type", "year"],
                name="unique_user_leave_balance_per_year",
            )
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
        ("withdrawn", "Withdrawn"),
    ]

    leave_type = models.ForeignKey(LeaveType, on_delete=models.PROTECT, related_name="requests")
    start_date = models.DateField()
    end_date = models.DateField()
    duration_days = models.DecimalField(max_digits=5, decimal_places=1)
    reason = models.TextField()
    half_day = models.CharField(
        max_length=8,
        choices=[("none", "None"), ("first", "First half"), ("second", "Second half")],
        default="none",
    )
    # Substitute / responsibility coverage
    substitute_user_id = models.IntegerField(null=True, blank=True)
    substitute_status = models.CharField(
        max_length=10,
        choices=[
            ("none", "None"),
            ("pending", "Pending"),
            ("accepted", "Accepted"),
            ("declined", "Declined"),
        ],
        default="none",
    )
    # Sanction routing
    unit_head_recommendation = models.CharField(
        max_length=16,
        choices=[
            ("none", "None"),
            ("recommended", "Recommended"),
            ("not_recommended", "Not Recommended"),
        ],
        default="none",
    )
    current_stage = models.CharField(
        max_length=16,
        choices=[
            ("unit_head", "Unit Head"),
            ("higher_sanction", "Higher Sanction"),
            ("director", "Director"),
        ],
        default="unit_head",
    )
    is_extension = models.BooleanField(default=False)
    parent_request_id = models.IntegerField(null=True, blank=True)
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


class RestrictedHoliday(TimeStampedModel):
    year = models.PositiveIntegerField(default=2026)
    date = models.DateField()
    name = models.CharField(max_length=120)
    is_published = models.BooleanField(default=True)

    class Meta:
        db_table = "restricted_holiday"
        unique_together = ("year", "date")

    def __str__(self):
        return f"{self.date} - {self.name}"


class LeaveResumption(TimeStampedModel, UserScopedModel):
    leave_request = models.ForeignKey(
        LeaveRequest, on_delete=models.CASCADE, related_name="resumptions"
    )
    actual_resumption_date = models.DateField()
    details = models.TextField(blank=True)
    status = models.CharField(
        max_length=12, choices=[("pending", "Pending"), ("reviewed", "Reviewed")], default="pending"
    )
    reviewed_by_user_id = models.IntegerField(null=True, blank=True)
    adjustment_days = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "leave_resumption"

    def __str__(self):
        return f"Resumption for leave #{self.leave_request_id}"


class LeaveSLAConfig(TimeStampedModel):
    reminder_days = models.PositiveIntegerField(default=3)
    escalation_days = models.PositiveIntegerField(default=7)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "leave_sla_config"
