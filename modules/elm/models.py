
from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel, UserScopedModel


class LeaveType(TimeStampedModel):
    """A leave category supported by the ELM policy."""

    TYPE_CHOICES = [
        ("CL", "Casual Leave"),
        ("RH", "Restricted Holiday"),
        ("SCL", "Special Casual Leave"),
        ("EL", "Earned Leave"),
        ("COL", "Commuted Leave"),
        ("VL", "Vacation Leave"),
    ]

    name = models.CharField(max_length=50, unique=True)
    type_code = models.CharField(
        max_length=3,
        choices=TYPE_CHOICES,
        unique=True,
    )

    class Meta:
        verbose_name = "Leave Type"
        verbose_name_plural = "Leave Types"
        ordering = ["type_code"]

    def __str__(self):
        return f"{self.name} ({self.type_code})"


class Office(TimeStampedModel):
    """An office that manages employee leave requests."""

    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=30, unique=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.code})"


class LeaveBalance(TimeStampedModel, UserScopedModel):
    """Current balance for one IAM user and one leave category."""

    leave_type = models.ForeignKey(
        LeaveType,
        on_delete=models.PROTECT,
        related_name="balances",
    )

    current_balance = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=0,
    )

    class Meta:
        verbose_name = "Leave Balance"
        verbose_name_plural = "Leave Balances"
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "leave_type"],
                name="elm_balance_user_type_uniq",
            ),
            models.CheckConstraint(
                condition=Q(current_balance__gte=0),
                name="elm_balance_nonnegative",
            ),
        ]

    def __str__(self):
        return f"IAM user {self.user_id} - {self.leave_type.type_code}"


class LeaveRequest(TimeStampedModel, UserScopedModel):
    """An employee's request for a period of leave."""

    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("WITHDRAWN", "Withdrawn"),
        ("CANCELLED", "Cancelled"),
    ]

    leave_type = models.ForeignKey(
        LeaveType,
        on_delete=models.PROTECT,
        related_name="requests",
    )

    # Office associated with the request when it is submitted.
    office = models.ForeignKey(
        Office,
        on_delete=models.PROTECT,
        related_name="leave_requests",
        null=True,
        blank=True,
    )

    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(blank=True)

    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default="PENDING",
    )

    # IAM identity of the authority who made the final decision.
    approver_id = models.IntegerField(
        null=True,
        blank=True,
        db_index=True,
    )

    approval_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Leave Request"
        verbose_name_plural = "Leave Requests"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(end_date__gte=models.F("start_date")),
                name="elm_request_valid_date_range",
            ),
        ]
        indexes = [
            models.Index(
                fields=["user_id", "status"],
                name="elm_request_user_status_idx",
            ),
            models.Index(
                fields=["start_date", "end_date"],
                name="elm_request_dates_idx",
            ),
        ]

    def __str__(self):
        return (
            f"IAM user {self.user_id} - "
            f"{self.start_date} to {self.end_date}"
        )


class EmployeeOfficeAssignment(TimeStampedModel):
    """Admin-managed mapping between an IAM employee and an office."""

    user_id = models.IntegerField(unique=True, db_index=True)

    office = models.ForeignKey(
        Office,
        on_delete=models.PROTECT,
        related_name="employee_assignments",
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Employee Office Assignment"
        verbose_name_plural = "Employee Office Assignments"

    def __str__(self):
        return f"IAM user {self.user_id} - {self.office.code}"


class OfficeApprover(TimeStampedModel):
    """An IAM user authorized to decide leave requests for an office."""

    user_id = models.IntegerField(db_index=True)

    office = models.ForeignKey(
        Office,
        on_delete=models.PROTECT,
        related_name="approvers",
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Office Approver"
        verbose_name_plural = "Office Approvers"
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "office"],
                name="elm_approver_user_office_uniq",
            ),
        ]

    def __str__(self):
        return f"IAM user {self.user_id} - {self.office.code}"
