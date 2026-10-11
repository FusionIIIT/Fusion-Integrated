from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator


class LeaveType(models.TextChoices):
    CL = "CL", "Casual Leave"
    RH = "RH", "Restricted Holiday"
    SCL = "SCL", "Special Casual Leave"
    EL = "EL", "Earned Leave"
    COL = "COL", "Commuted Leave"
    VL = "VL", "Vacation Leave"


class LeaveStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    AWAITING_SUBSTITUTE = (
        "AWAITING_SUBSTITUTE",
        "Awaiting Substitute Response",
    )
    PENDING_UNIT_HEAD = (
        "PENDING_UNIT_HEAD",
        "Pending Unit Head Review",
    )
    PENDING_AUTHORITY = (
        "PENDING_AUTHORITY",
        "Pending Sanctioning Authority",
    )
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    WITHDRAWN = "WITHDRAWN", "Withdrawn"
    ACTION_REQUIRED = "ACTION_REQUIRED", "Applicant Action Required"


class LeaveAccount(models.Model):
    """An employee's account for a particular leave category and year."""

    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="elm_leave_accounts",
    )
    leave_type = models.CharField(
        max_length=3,
        choices=LeaveType.choices,
    )
    year = models.PositiveIntegerField()
    entitlement = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )
    opening_balance = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        default=0,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["employee", "leave_type", "year"],
                name="elm_unique_employee_type_year",
            ),
        ]

    def __str__(self):
        return (
            f"{self.employee_id} - {self.leave_type} "
            f"({self.year})"
        )


class LeaveApplication(models.Model):
    """One leave request, including any associated station-leave details."""

    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="elm_applications",
    )
    leave_type = models.CharField(
        max_length=3,
        choices=LeaveType.choices,
    )
    start_date = models.DateField()
    end_date = models.DateField()
    purpose = models.TextField()
    status = models.CharField(
        max_length=24,
        choices=LeaveStatus.choices,
        default=LeaveStatus.DRAFT,
    )

    # Optional fields for leave types that support half-day CL.
    start_half = models.CharField(
        max_length=10,
        blank=True,
        choices=[
            ("FULL", "Full day"),
            ("FIRST", "First half"),
            ("SECOND", "Second half"),
        ],
        default="FULL",
    )
    end_half = models.CharField(
        max_length=10,
        blank=True,
        choices=[
            ("FULL", "Full day"),
            ("FIRST", "First half"),
            ("SECOND", "Second half"),
        ],
        default="FULL",
    )

    # Station Leave belongs to the same application.
    station_leave_required = models.BooleanField(default=False)
    station_leave_details = models.TextField(blank=True)

    substitute = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="elm_substitute_requests",
    )
    substitute_accepted = models.BooleanField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["employee", "status"],
                name="elm_employee_status_idx",
            ),
            models.Index(
                fields=["start_date", "end_date"],
                name="elm_leave_dates_idx",
            ),
        ]

    def __str__(self):
        return (
            f"Leave #{self.pk}: {self.employee_id} "
            f"({self.leave_type})"
        )


class LeaveBalanceTransaction(models.Model):
    """Audit trail for changes to a leave account."""

    account = models.ForeignKey(
        LeaveAccount,
        on_delete=models.PROTECT,
        related_name="transactions",
    )
    application = models.ForeignKey(
        LeaveApplication,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="balance_transactions",
    )
    amount = models.DecimalField(
        max_digits=7,
        decimal_places=2,
    )
    reason = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
