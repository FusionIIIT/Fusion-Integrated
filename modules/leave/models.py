from django.db import models
from core.db.mixins import TimeStampedModel, UserScopedModel
from modules.leave.domain.rules import HALF_DAY_CHOICES, HALF_DAY_NONE


class LeaveType(TimeStampedModel):
    CL = "CL"
    RH = "RH"
    SCL = "SCL"
    EL = "EL"
    COL = "COL"
    VL = "VL"

    CATEGORY_CHOICES = [
        (CL, "Casual Leave"),
        (RH, "Restricted Holiday"),
        (SCL, "Special Casual Leave"),
        (EL, "Earned Leave"),
        (COL, "Commuted / Caregiver Leave"),
        (VL, "Vacation Leave"),
    ]

    code = models.CharField(max_length=10, unique=True, choices=CATEGORY_CHOICES)
    name = models.CharField(max_length=80)
    max_days_per_year = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)
    carry_forward = models.BooleanField(default=False)
    requires_substitute = models.BooleanField(default=False)
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
            models.UniqueConstraint(fields=["user_id", "leave_type", "year"], name="unique_user_leave_balance_year")
        ]

    @property
    def remaining_days(self):
        return max(0.0, float(self.allocated_days) - float(self.used_days))

    def __str__(self):
        return f"User {self.user_id} - {self.leave_type.code}: {self.remaining_days} days remaining"


class LeaveRequest(TimeStampedModel, UserScopedModel):
    STATUS_CHOICES = [
        ("pending", "Pending Approval"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("cancelled", "Cancelled"),
        ("withdrawn", "Withdrawn"),
    ]

    SUBSTITUTE_STATUS_CHOICES = [
        ("none", "Not Required"),
        ("pending", "Pending Consent"),
        ("accepted", "Accepted"),
        ("declined", "Declined"),
    ]

    RECOMMENDATION_CHOICES = [
        ("none", "None"),
        ("recommended", "Recommended"),
        ("not_recommended", "Not Recommended"),
    ]

    leave_type = models.ForeignKey(LeaveType, on_delete=models.PROTECT, related_name="requests")
    start_date = models.DateField()
    end_date = models.DateField()
    duration_days = models.DecimalField(max_digits=5, decimal_places=1)
    half_day_period = models.CharField(max_length=20, choices=HALF_DAY_CHOICES, default=HALF_DAY_NONE)
    reason = models.TextField()
    is_station_leave = models.BooleanField(default=False)
    station_details = models.CharField(max_length=255, blank=True, default="")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    # Substitute workflow (BR-EL-014, BR-EL-015)
    substitute_user_id = models.IntegerField(null=True, blank=True)
    substitute_status = models.CharField(max_length=20, choices=SUBSTITUTE_STATUS_CHOICES, default="none")

    # Sanctioning / Recommendation workflow (BR-EL-016, BR-EL-017, BR-EL-018)
    approver_user_id = models.IntegerField(null=True, blank=True)
    rejection_reason = models.CharField(max_length=255, blank=True, default="")
    approved_at = models.DateTimeField(null=True, blank=True)

    recommendation = models.CharField(max_length=20, choices=RECOMMENDATION_CHOICES, default="none")
    recommended_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "leave_request"
        indexes = [
            models.Index(fields=["user_id", "status"], name="leave_req_user_idx"),
            models.Index(fields=["approver_user_id", "status"], name="leave_req_approver_idx"),
            models.Index(fields=["substitute_user_id", "substitute_status"], name="leave_req_sub_idx"),
        ]

    def __str__(self):
        return f"LeaveRequest #{self.pk} by {self.user_id} ({self.status})"
