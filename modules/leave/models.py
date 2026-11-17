from decimal import Decimal
from django.db import models
from core.db.mixins import TimeStampedModel, UserScopedModel


class LeaveType(TimeStampedModel):
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=60)
    max_days_per_year = models.PositiveSmallIntegerField(default=12)
    allows_half_day = models.BooleanField(default=False)
    requires_attachment = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "leave_type"

    def __str__(self):
        return f"{self.code} - {self.name}"


class LeaveBalance(TimeStampedModel, UserScopedModel):
    leave_type = models.ForeignKey(LeaveType, on_delete=models.PROTECT, related_name="balances")
    year = models.PositiveIntegerField(default=2026)
    allocated_days = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal("0.0"))
    used_days = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal("0.0"))

    class Meta:
        db_table = "leave_balance"
        constraints = [
            models.UniqueConstraint(fields=["user_id", "leave_type", "year"], name="unique_user_leave_balance_per_year")
        ]

    @property
    def remaining_days(self) -> float:
        return float(self.allocated_days) - float(self.used_days)

    def __str__(self):
        return f"User {self.user_id} - {self.leave_type.code}: {self.remaining_days} remaining"


class LeaveRequest(TimeStampedModel, UserScopedModel):
    STATUS_CHOICES = [
        ("DRAFT", "Draft"),
        ("PENDING_APPROVAL", "Pending Approval"),
        ("RECOMMENDED", "Recommended"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("CANCELLED", "Cancelled"),
    ]

    SLOT_CHOICES = [
        ("FORENOON", "Forenoon (First Half)"),
        ("AFTERNOON", "Afternoon (Second Half)"),
    ]

    leave_type = models.ForeignKey(LeaveType, on_delete=models.PROTECT, related_name="requests")
    start_date = models.DateField()
    end_date = models.DateField()
    duration_days = models.DecimalField(max_digits=5, decimal_places=1)
    is_half_day = models.BooleanField(default=False)
    half_day_slot = models.CharField(max_length=15, choices=SLOT_CHOICES, blank=True)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="PENDING_APPROVAL")

    # Station Leave fields (BR-EL-013)
    is_station_leave = models.BooleanField(default=False)
    station_start_date = models.DateField(null=True, blank=True)
    station_end_date = models.DateField(null=True, blank=True)
    station_address = models.CharField(max_length=255, blank=True)
    emergency_contact_no = models.CharField(max_length=20, blank=True)

    # Attachments (e.g. medical certificate for COL)
    attachment_path = models.CharField(max_length=255, blank=True)

    # Workflow & Approvals
    recommender_user_id = models.IntegerField(null=True, blank=True)
    recommendation_remarks = models.TextField(blank=True)
    recommended_at = models.DateTimeField(null=True, blank=True)

    approver_user_id = models.IntegerField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    approval_remarks = models.TextField(blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "leave_request"
        indexes = [
            models.Index(fields=["user_id", "status"], name="leave_req_user_status_idx"),
            models.Index(fields=["approver_user_id", "status"], name="leave_req_appr_status_idx"),
            models.Index(fields=["recommender_user_id", "status"], name="leave_req_recm_status_idx"),
        ]

    def __str__(self):
        return f"Leave #{self.pk} by User {self.user_id} ({self.status})"


class LeaveLedger(TimeStampedModel, UserScopedModel):
    TRANSACTION_CHOICES = [
        ("CREDIT", "Credit"),
        ("DEBIT", "Debit"),
        ("RESTORE", "Restore"),
        ("ADJUSTMENT", "Adjustment"),
    ]

    leave_type = models.ForeignKey(LeaveType, on_delete=models.PROTECT, related_name="ledger_entries")
    transaction_type = models.CharField(max_length=15, choices=TRANSACTION_CHOICES)
    days = models.DecimalField(max_digits=5, decimal_places=1)
    balance_after = models.DecimalField(max_digits=5, decimal_places=1)
    reference_request = models.ForeignKey(
        LeaveRequest, on_delete=models.SET_NULL, null=True, blank=True, related_name="ledger_entries"
    )
    remarks = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "leave_ledger"
        indexes = [
            models.Index(fields=["user_id", "leave_type"], name="leave_ledger_user_type_idx"),
        ]

    def __str__(self):
        return f"Ledger #{self.pk} User {self.user_id} {self.transaction_type} {self.days}d"
