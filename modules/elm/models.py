"""Employee Leave Management domain tables.

Fusion identities are stored as integer user IDs. IAM remains the source of
identity and authorization; this module does not create its own user/role tables.
"""
from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel


class LeaveTypePolicy(TimeStampedModel):
    CL = "CL"
    RH = "RH"
    SCL = "SCL"
    EL = "EL"
    COL = "COL"
    VL = "VL"
    LEAVE_TYPES = [
        (CL, "Casual Leave"),
        (RH, "Restricted Holiday"),
        (SCL, "Special Casual Leave"),
        (EL, "Earned Leave"),
        (COL, "Compensatory Leave"),
        (VL, "Vacation Leave"),
    ]
    EMPLOYEE_CATEGORIES = [
        ("any", "Any eligible employee"),
        ("faculty", "Faculty"),
        ("non_faculty", "Non-faculty"),
    ]

    code = models.CharField(max_length=3, choices=LEAVE_TYPES, unique=True)
    annual_allowance = models.DecimalField(max_digits=7, decimal_places=2)
    carry_forward = models.BooleanField(default=False)
    continuous_calendar_days = models.BooleanField(default=False)
    employee_category = models.CharField(
        max_length=16, choices=EMPLOYEE_CATEGORIES, default="any"
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "elm_leave_type_policy"
        ordering = ["code"]

    def __str__(self):
        return self.code


class LeaveAccount(TimeStampedModel):
    user_id = models.PositiveBigIntegerField(db_index=True)
    employee_category = models.CharField(
        max_length=16, choices=LeaveTypePolicy.EMPLOYEE_CATEGORIES, default="any"
    )
    leave_type = models.ForeignKey(
        LeaveTypePolicy, on_delete=models.PROTECT, related_name="accounts"
    )
    leave_year = models.PositiveSmallIntegerField()
    balance_days = models.DecimalField(max_digits=7, decimal_places=2, default=0)

    class Meta:
        db_table = "elm_leave_account"
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "leave_type", "leave_year"],
                name="elm_account_user_type_year_uniq",
            ),
            models.CheckConstraint(
                condition=Q(balance_days__gte=0), name="elm_account_balance_nonnegative"
            ),
        ]
        indexes = [models.Index(fields=["user_id", "leave_year"], name="elm_account_user_year_idx")]

    def __str__(self):
        return f"{self.user_id}:{self.leave_type_id}:{self.leave_year}"


class LeaveRequest(TimeStampedModel):
    PENDING_UNIT_HEAD = "pending_unit_head"
    PENDING_HIERARCHY = "pending_hierarchy"
    APPROVED = "approved"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    CANCELLATION_PENDING = "cancellation_pending"
    CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (PENDING_UNIT_HEAD, "Pending Unit Head"),
        (PENDING_HIERARCHY, "Pending final approval"),
        (APPROVED, "Approved"),
        (REJECTED, "Rejected"),
        (WITHDRAWN, "Withdrawn"),
        (CANCELLATION_PENDING, "Cancellation pending"),
        (CANCELLED, "Cancelled"),
    ]
    SESSION_CHOICES = [
        ("full", "Full day"),
        ("first_half", "First half"),
        ("second_half", "Second half"),
    ]
    SUBSTITUTE_STATES = [
        ("not_required", "Not required"),
        ("awaiting", "Awaiting consent"),
        ("accepted", "Accepted"),
        ("declined", "Declined"),
    ]

    user_id = models.PositiveBigIntegerField(db_index=True)
    employee_category = models.CharField(
        max_length=16, choices=LeaveTypePolicy.EMPLOYEE_CATEGORIES
    )
    leave_type = models.ForeignKey(
        LeaveTypePolicy, on_delete=models.PROTECT, related_name="requests"
    )
    start_date = models.DateField()
    end_date = models.DateField()
    start_session = models.CharField(max_length=16, choices=SESSION_CHOICES, default="full")
    end_session = models.CharField(max_length=16, choices=SESSION_CHOICES, default="full")
    requested_days = models.DecimalField(max_digits=7, decimal_places=2)
    reason = models.TextField(max_length=2000)
    status = models.CharField(
        max_length=24, choices=STATUS_CHOICES, default=PENDING_UNIT_HEAD, db_index=True
    )
    substitute_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    substitute_consent = models.CharField(
        max_length=16, choices=SUBSTITUTE_STATES, default="not_required"
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "elm_leave_request"
        constraints = [
            models.CheckConstraint(
                condition=Q(end_date__gte=models.F("start_date")),
                name="elm_request_dates_ordered",
            ),
            models.CheckConstraint(
                condition=Q(requested_days__gt=0), name="elm_request_days_positive"
            ),
        ]
        indexes = [
            models.Index(fields=["user_id", "status"], name="elm_request_user_status_idx"),
            models.Index(fields=["start_date", "end_date", "status"], name="elm_request_dates_status_idx"),
        ]

    def __str__(self):
        return f"Leave request {self.pk} by {self.user_id}"


class LeaveRequestTransition(TimeStampedModel):
    request = models.ForeignKey(
        LeaveRequest, on_delete=models.PROTECT, related_name="transitions"
    )
    from_status = models.CharField(max_length=24, blank=True)
    to_status = models.CharField(max_length=24)
    actor_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    action = models.CharField(max_length=40)
    reason = models.CharField(max_length=1000, blank=True)

    class Meta:
        db_table = "elm_leave_request_transition"
        ordering = ["created_at", "pk"]


class LeaveBalanceTransaction(TimeStampedModel):
    CREDIT = "credit"
    DEBIT = "debit"
    REVERSAL = "reversal"
    CARRY_FORWARD = "carry_forward"
    VL_CONVERSION = "vl_conversion"
    TRANSACTION_TYPES = [
        (CREDIT, "Credit"),
        (DEBIT, "Debit"),
        (REVERSAL, "Reversal"),
        (CARRY_FORWARD, "Carry forward"),
        (VL_CONVERSION, "Vacation conversion"),
    ]

    account = models.ForeignKey(
        LeaveAccount, on_delete=models.PROTECT, related_name="transactions"
    )
    request = models.ForeignKey(
        LeaveRequest, null=True, blank=True, on_delete=models.PROTECT,
        related_name="balance_transactions",
    )
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount_days = models.DecimalField(max_digits=7, decimal_places=2)
    reason = models.CharField(max_length=1000)
    actor_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    idempotency_key = models.CharField(max_length=120, unique=True, null=True, blank=True)

    class Meta:
        db_table = "elm_leave_balance_transaction"
        ordering = ["created_at", "pk"]
        indexes = [models.Index(fields=["account", "created_at"], name="elm_balance_tx_account_idx")]


class LeaveCalendarDay(TimeStampedModel):
    RH_DAY = "rh"
    CLOSED_HOLIDAY = "closed_holiday"
    DAY_TYPES = [(RH_DAY, "Restricted holiday"), (CLOSED_HOLIDAY, "Closed holiday")]

    date = models.DateField()
    day_type = models.CharField(max_length=20, choices=DAY_TYPES)
    title = models.CharField(max_length=200)
    published = models.BooleanField(default=False)
    effective_from = models.DateField(null=True, blank=True)
    effective_until = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "elm_leave_calendar_day"
        constraints = [
            models.UniqueConstraint(
                fields=["date", "day_type", "title"], name="elm_calendar_day_uniq"
            ),
        ]
        indexes = [models.Index(fields=["date", "day_type", "published"], name="elm_calendar_lookup_idx")]


class LeaveCancellationRequest(TimeStampedModel):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    STATUS_CHOICES = [(PENDING, "Pending"), (APPROVED, "Approved"), (REJECTED, "Rejected")]

    leave_request = models.ForeignKey(
        LeaveRequest, on_delete=models.PROTECT, related_name="cancellations"
    )
    requested_by_user_id = models.PositiveBigIntegerField()
    reason = models.CharField(max_length=1000)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=PENDING)
    decided_by_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "elm_leave_cancellation_request"


class YearEndRun(TimeStampedModel):
    leave_year = models.PositiveSmallIntegerField()
    run_key = models.CharField(max_length=80, unique=True)
    status = models.CharField(max_length=16, default="completed")
    summary = models.JSONField(default=dict)

    class Meta:
        db_table = "elm_year_end_run"
