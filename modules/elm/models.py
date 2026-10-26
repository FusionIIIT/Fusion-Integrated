
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from core.db.mixins import TimeStampedModel


class LeaveType(TimeStampedModel):
    code = models.CharField(max_length=8, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    annual_quota = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    carries_forward = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} - {self.name}"


class LeaveBalance(TimeStampedModel):
    user_id = models.IntegerField(db_index=True)
    leave_type = models.ForeignKey(
        LeaveType, on_delete=models.PROTECT, related_name="balances"
    )
    balance = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    year = models.PositiveSmallIntegerField(default=timezone.now().year)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "leave_type", "year"],
                name="elm_unique_balance_per_year",
            ),
            models.CheckConstraint(
                condition=models.Q(balance__gte=0),
                name="elm_balance_nonnegative",
            ),
        ]

    def __str__(self):
        return f"User {self.user_id}: {self.leave_type.code} ({self.balance})"


class LeaveApplication(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING = "pending", "Pending"
        RECOMMENDED = "recommended", "Recommended"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        WITHDRAWN = "withdrawn", "Withdrawn"
        CANCELLED = "cancelled", "Cancelled"

    user_id = models.IntegerField(db_index=True)
    leave_type = models.ForeignKey(
        LeaveType, on_delete=models.PROTECT, related_name="applications"
    )
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(blank=True)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user_id", "status"]),
            models.Index(fields=["start_date", "end_date"]),
        ]

    def clean(self):
        super().clean()
        if self.end_date < self.start_date:
            raise ValidationError({"end_date": "End date cannot precede start date."})

    def __str__(self):
        return (
            f"User {self.user_id}: {self.leave_type.code} "
            f"({self.start_date} to {self.end_date})"
        )


class LeaveSubstitute(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACCEPTED = "accepted", "Accepted"
        DECLINED = "declined", "Declined"

    user_id = models.IntegerField(db_index=True)
    leave_application = models.ForeignKey(
        LeaveApplication, on_delete=models.CASCADE, related_name="substitutes"
    )
    substitute_user_id = models.IntegerField(db_index=True)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.PENDING
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(user_id=models.F("substitute_user_id")),
                name="elm_substitute_not_applicant",
            ),
        ]

    def clean(self):
        super().clean()
        if self.end_date < self.start_date:
            raise ValidationError({"end_date": "End date cannot precede start date."})
        if self.user_id == self.substitute_user_id:
            raise ValidationError(
                {"substitute_user_id": "The applicant cannot substitute for themselves."}
            )

    def __str__(self):
        return f"Substitute {self.substitute_user_id} for leave {self.leave_application_id}"


class LeaveApproval(TimeStampedModel):
    class Decision(models.TextChoices):
        PENDING = "pending", "Pending"
        RECOMMENDED = "recommended", "Recommended"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    user_id = models.IntegerField(db_index=True)
    leave_application = models.ForeignKey(
        LeaveApplication, on_delete=models.CASCADE, related_name="approvals"
    )
    approver_user_id = models.IntegerField(db_index=True)
    stage = models.PositiveSmallIntegerField(default=1)
    decision = models.CharField(
        max_length=16, choices=Decision.choices, default=Decision.PENDING
    )
    comments = models.TextField(blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["stage", "created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["leave_application", "stage"],
                name="elm_unique_approval_stage",
            ),
        ]

    def __str__(self):
        return f"Approval stage {self.stage} for leave {self.leave_application_id}"


class LeaveCalendarPeriod(TimeStampedModel):
    """A configured period during which a leave category is available."""

    name = models.CharField(max_length=120)
    start_date = models.DateField()
    end_date = models.DateField()
    leave_type = models.ForeignKey(
        LeaveType,
        on_delete=models.CASCADE,
        related_name="calendar_periods",
        null=True,
        blank=True,
    )
    is_vacation = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["start_date", "name"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_date__gte=models.F("start_date")),
                name="elm_calendar_period_dates_valid",
            ),
        ]

    def clean(self):
        super().clean()
        if self.end_date < self.start_date:
            raise ValidationError(
                {"end_date": "End date cannot precede start date."}
            )

    def __str__(self):
        return f"{self.name} ({self.start_date} to {self.end_date})"


class LeaveBalanceTransaction(TimeStampedModel):
    """Auditable record of a leave balance credit, debit, or adjustment."""

    class TransactionType(models.TextChoices):
        CREDIT = "credit", "Credit"
        DEBIT = "debit", "Debit"
        CARRY_FORWARD = "carry_forward", "Carry forward"
        CONVERSION = "conversion", "Leave conversion"
        ADJUSTMENT = "adjustment", "Manual adjustment"

    balance = models.ForeignKey(
        LeaveBalance,
        on_delete=models.PROTECT,
        related_name="transactions",
    )
    amount = models.DecimalField(max_digits=7, decimal_places=2)
    transaction_type = models.CharField(
        max_length=20,
        choices=TransactionType.choices,
    )
    reference = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)
    performed_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["balance", "created_at"]),
        ]

    def clean(self):
        super().clean()
        if self.amount == 0:
            raise ValidationError({"amount": "Transaction amount cannot be zero."})

    def __str__(self):
        return (
            f"{self.transaction_type}: {self.amount} "
            f"for balance {self.balance_id}"
        )
