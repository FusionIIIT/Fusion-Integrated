"""Leave applications, balances and substitute assignments."""

from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel, UserScopedModel


class LeaveCategory(TimeStampedModel):
    CODE_CHOICES = [
        ("CL", "Casual Leave"),
        ("RH", "Restricted Holiday"),
        ("SCL", "Special Casual Leave"),
        ("EL", "Earned Leave"),
        ("COL", "Commuted Leave"),
        ("VL", "Vacation Leave"),
    ]

    code = models.CharField(max_length=8, choices=CODE_CHOICES, unique=True)
    name = models.CharField(max_length=80)
    description = models.TextField(blank=True)
    annual_entitlement = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    carry_forward = models.BooleanField(default=False)
    continuous_counting = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "leave_category"
        ordering = ["code"]

    def __str__(self) -> str:
        return self.name


class LeaveApplication(TimeStampedModel, UserScopedModel):
    STATUS = [
        ("draft", "Draft"),
        ("awaiting_substitute", "Awaiting substitute"),
        ("awaiting_unit_head", "Awaiting Unit Head"),
        ("awaiting_establishment", "Awaiting Establishment"),
        ("awaiting_sanction", "Awaiting final sanction"),
        ("awaiting_self_sanction", "Awaiting self-sanction"),
        ("applicant_action_required", "Applicant action required"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("withdrawn", "Withdrawn"),
        ("cancelled", "Cancelled"),
    ]
    HALF_DAY_CHOICES = [("full", "Full day"), ("first", "First half"), ("second", "Second half")]

    category = models.ForeignKey(
        LeaveCategory, on_delete=models.PROTECT, related_name="applications"
    )
    status = models.CharField(max_length=32, choices=STATUS, default="draft")
    applicant_role = models.CharField(max_length=80, blank=True)
    assigned_role = models.CharField(max_length=80, blank=True)
    starts_on = models.DateField()
    ends_on = models.DateField()
    half_day = models.CharField(max_length=8, choices=HALF_DAY_CHOICES, default="full")
    requested_days = models.DecimalField(max_digits=7, decimal_places=2)
    requested_days_by_year = models.JSONField(default=dict, blank=True)
    purpose = models.TextField()
    station_leave = models.BooleanField(default=False)
    station_destination = models.CharField(max_length=160, blank=True)
    substitute_user_id = models.IntegerField(null=True, blank=True)
    substitute_response = models.CharField(max_length=12, blank=True)
    medical_evidence_reference = models.CharField(max_length=500, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "leave_application"
        constraints = [
            models.CheckConstraint(
                condition=Q(ends_on__gte=models.F("starts_on")), name="leave_app_dates_valid"
            ),
            models.CheckConstraint(
                condition=Q(requested_days__gt=0), name="leave_app_days_positive"
            ),
        ]
        indexes = [
            models.Index(fields=["user_id", "status"], name="leave_app_user_status_idx"),
            models.Index(fields=["category", "status"], name="leave_app_cat_status_idx"),
            models.Index(fields=["starts_on", "ends_on"], name="leave_app_dates_idx"),
        ]

    def __str__(self) -> str:
        return f"leave#{self.pk} u{self.user_id} {self.status}"


class LeaveApplicationTransition(models.Model):
    application = models.ForeignKey(
        LeaveApplication, on_delete=models.CASCADE, related_name="transitions"
    )
    from_status = models.CharField(max_length=32)
    to_status = models.CharField(max_length=32)
    actor_user_id = models.IntegerField(null=True, blank=True)
    actor_label = models.CharField(max_length=80, blank=True)
    reason = models.CharField(max_length=300, blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "leave_application_transition"
        indexes = [models.Index(fields=["application", "at"], name="leave_transition_app_idx")]

    def __str__(self) -> str:
        return f"leave#{self.application_id} {self.from_status}->{self.to_status}"


class LeaveBalance(TimeStampedModel):
    user_id = models.IntegerField(db_index=True)
    category = models.ForeignKey(LeaveCategory, on_delete=models.PROTECT, related_name="balances")
    year = models.PositiveSmallIntegerField()
    opening_balance = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    credited = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    used = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    closing_balance = models.DecimalField(max_digits=8, decimal_places=2, default=0)

    class Meta:
        db_table = "leave_balance"
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "category", "year"], name="leave_balance_user_category_year_uniq"
            ),
            models.CheckConstraint(
                condition=Q(closing_balance__gte=0), name="leave_balance_nonnegative"
            ),
        ]

    def __str__(self) -> str:
        return f"u{self.user_id} {self.category.code} {self.year}: {self.closing_balance}"


class LeaveBalanceTransaction(models.Model):
    TYPES = [
        ("accrual", "Accrual"),
        ("deduction", "Deduction"),
        ("carry_forward", "Carry forward"),
        ("conversion", "Conversion"),
        ("adjustment", "Adjustment"),
        ("restoration", "Restoration"),
        ("lapse", "Lapse"),
    ]

    balance = models.ForeignKey(LeaveBalance, on_delete=models.CASCADE, related_name="transactions")
    application = models.ForeignKey(
        LeaveApplication,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="balance_transactions",
    )
    transaction_type = models.CharField(max_length=20, choices=TYPES)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    note = models.CharField(max_length=300, blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "leave_balance_transaction"
        indexes = [models.Index(fields=["balance", "at"], name="leave_transaction_balance_idx")]

    def __str__(self) -> str:
        return f"transaction#{self.pk} {self.transaction_type} {self.amount}"


class Substitute(TimeStampedModel):
    STATUS = [
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("declined", "Declined"),
        ("replaced", "Replaced"),
    ]

    application = models.ForeignKey(
        LeaveApplication, on_delete=models.CASCADE, related_name="substitute_assignments"
    )
    user_id = models.IntegerField(db_index=True)
    substitute_user_id = models.IntegerField(db_index=True)
    status = models.CharField(max_length=12, choices=STATUS, default="pending")
    response_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "leave_substitute"
        indexes = [
            models.Index(
                fields=["substitute_user_id", "status"], name="leave_substitute_pending_idx"
            )
        ]
