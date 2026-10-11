"""ELM-owned tables. User identities are IAM ids; no cross-module foreign keys."""
from django.db import models
from django.utils import timezone
from core.db.mixins import TimeStampedModel


class LeavePolicy(TimeStampedModel):
    category = models.CharField(max_length=12, unique=True)
    annual_entitlement = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    carry_forward_limit = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    applies_to = models.JSONField(default=list, blank=True)
    requires_substitute = models.BooleanField(default=False)
    counts_closed_days = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "elm_leave_policy"
        ordering = ["category"]


class LeaveBalance(TimeStampedModel):
    user_id = models.IntegerField(db_index=True)
    category = models.CharField(max_length=12)
    leave_year = models.PositiveSmallIntegerField(db_index=True)
    opening = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    credited = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    consumed = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    adjusted = models.DecimalField(max_digits=7, decimal_places=2, default=0)

    class Meta:
        db_table = "elm_leave_balance"
        constraints = [models.UniqueConstraint(fields=["user_id", "category", "leave_year"], name="elm_balance_user_cat_year_uniq")]
        indexes = [models.Index(fields=["user_id", "leave_year"], name="elm_balance_user_year_idx")]

    @property
    def available(self):
        return self.opening + self.credited + self.adjusted - self.consumed


class LeaveRequest(TimeStampedModel):
    CATEGORY_CHOICES = [(x, x) for x in ("CL", "RH", "SCL", "EL", "VL", "COL")]
    STATUS_CHOICES = [(x, x.replace("_", " ").title()) for x in (
        "draft", "awaiting_substitute", "pending_unit_head", "pending_authority",
        "pending_establishment", "approved", "rejected", "withdrawn", "cancelled")]
    user_id = models.IntegerField(db_index=True)
    category = models.CharField(max_length=12, choices=CATEGORY_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    duration_days = models.DecimalField(max_digits=6, decimal_places=2)
    half_day = models.BooleanField(default=False)
    half_day_period = models.CharField(max_length=8, blank=True)
    station_leave_required = models.BooleanField(default=False)
    station_leave_from = models.DateTimeField(null=True, blank=True)
    station_leave_until = models.DateTimeField(null=True, blank=True)
    substitute_user_id = models.IntegerField(null=True, blank=True)
    substitute_consent = models.CharField(max_length=10, choices=[("pending", "Pending"), ("accepted", "Accepted"), ("declined", "Declined"), ("not_required", "Not required")], default="not_required")
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default="pending_unit_head", db_index=True)
    current_approver_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    submitted_at = models.DateTimeField(default=timezone.now)
    decided_at = models.DateTimeField(null=True, blank=True)
    related_request_id = models.IntegerField(null=True, blank=True, db_index=True)
    source = models.CharField(max_length=16, choices=[("portal", "Portal"), ("offline", "Offline")], default="portal")
    external_reference = models.CharField(max_length=100, blank=True)

    class Meta:
        db_table = "elm_leave_request"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user_id", "status"], name="elm_req_user_status_idx"), models.Index(fields=["start_date", "end_date"], name="elm_req_dates_idx")]


class ApprovalTask(TimeStampedModel):
    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE, related_name="tasks")
    stage = models.CharField(max_length=24)
    approver_user_id = models.IntegerField(db_index=True)
    status = models.CharField(max_length=12, choices=[("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected"), ("superseded", "Superseded"), ("cancelled", "Cancelled")], default="pending", db_index=True)
    decision_note = models.TextField(blank=True)
    acted_at = models.DateTimeField(null=True, blank=True)
    due_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "elm_approval_task"
        ordering = ["created_at"]
        indexes = [models.Index(fields=["approver_user_id", "status"], name="elm_task_approver_status_idx")]


class LeaveCalendarDay(TimeStampedModel):
    date = models.DateField(unique=True)
    title = models.CharField(max_length=120)
    day_type = models.CharField(max_length=12, choices=[("holiday", "Holiday"), ("restricted", "Restricted Holiday"), ("working", "Working Day")])
    is_published = models.BooleanField(default=False)

    class Meta:
        db_table = "elm_calendar_day"
        ordering = ["date"]


class ResumptionRecord(TimeStampedModel):
    request = models.OneToOneField(LeaveRequest, on_delete=models.PROTECT, related_name="resumption")
    reported_on = models.DateField()
    remarks = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=[("pending", "Pending"), ("normal", "Normal"), ("early", "Early"), ("late", "Late")], default="pending")
    verified_by_user_id = models.IntegerField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "elm_resumption_record"
