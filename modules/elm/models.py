from decimal import Decimal

from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel


class LeaveCategory(TimeStampedModel):
    """Leave category configuration (CL, RH, SCL, EL, COL, VL)."""

    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    annual_quota = models.DecimalField(
        max_digits=5, decimal_places=1, default=Decimal("0.0")
    )
    carries_forward = models.BooleanField(default=False)
    continuous_counting = models.BooleanField(default=False)
    faculty_only = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "elm_leave_category"
        verbose_name_plural = "Leave Categories"

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class LeaveApplication(TimeStampedModel, UserScopedModel):
    """An employee leave application with workflow state and station details."""

    STATUS_PENDING_SUBSTITUTE = "pending_substitute"
    STATUS_SUBMITTED = "submitted"
    STATUS_PENDING_SANCTION = "pending_sanction"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_WITHDRAWN = "withdrawn"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_PENDING_SUBSTITUTE, "Awaiting Substitute Consent"),
        (STATUS_SUBMITTED, "Pending Unit Head Review"),
        (STATUS_PENDING_SANCTION, "Pending Sanctioning Authority"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_WITHDRAWN, "Withdrawn"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    HALF_DAY_CHOICES = [
        ("none", "Full Day"),
        ("first_half", "First Half"),
        ("second_half", "Second Half"),
    ]

    category = models.ForeignKey(
        LeaveCategory,
        on_delete=models.PROTECT,
        related_name="applications",
    )
    start_date = models.DateField()
    end_date = models.DateField()
    half_day = models.CharField(
        max_length=20, choices=HALF_DAY_CHOICES, default="none"
    )
    days_count = models.DecimalField(
        max_digits=5, decimal_places=1, default=Decimal("1.0")
    )
    reason = models.TextField()
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default=STATUS_SUBMITTED,
        db_index=True,
    )

    # Station Leave details (inside same application)
    station_leave = models.BooleanField(default=False)
    station_address = models.TextField(blank=True)
    station_start_date = models.DateField(null=True, blank=True)
    station_end_date = models.DateField(null=True, blank=True)
    emergency_contact = models.CharField(max_length=30, blank=True)

    # Substitute coverage
    substitute_id = models.IntegerField(null=True, blank=True, db_index=True)
    substitute_status = models.CharField(
        max_length=20,
        choices=[
            ("none", "None"),
            ("pending", "Pending"),
            ("accepted", "Accepted"),
            ("declined", "Declined"),
        ],
        default="none",
    )
    substitute_remarks = models.TextField(blank=True)
    substitute_acted_at = models.DateTimeField(null=True, blank=True)

    # Unit Head Review
    unit_head_id = models.IntegerField(null=True, blank=True)
    unit_head_recommendation = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("recommended", "Recommended"),
            ("not_recommended", "Not Recommended"),
        ],
        default="pending",
    )
    unit_head_remarks = models.TextField(blank=True)
    unit_head_acted_at = models.DateTimeField(null=True, blank=True)

    # Final Sanctioning Authority
    sanctioning_authority_id = models.IntegerField(null=True, blank=True)
    sanction_remarks = models.TextField(blank=True)
    sanction_acted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "elm_leave_application"
        verbose_name_plural = "Leave Applications"
        indexes = [
            models.Index(fields=["user_id", "status"], name="elm_app_user_status_idx"),
            models.Index(fields=["status", "start_date"], name="elm_app_status_start_idx"),
            models.Index(
                fields=["substitute_id", "substitute_status"],
                name="elm_app_sub_status_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"User {self.user_id} - {self.category.code} - {self.status}"


class LeaveBalance(TimeStampedModel, UserScopedModel):
    """Leave balance tracking for an employee per category and year."""

    category = models.ForeignKey(
        LeaveCategory,
        on_delete=models.PROTECT,
        related_name="balances",
    )
    year = models.IntegerField(default=2026)
    credited = models.DecimalField(
        max_digits=5, decimal_places=1, default=Decimal("0.0")
    )
    consumed = models.DecimalField(
        max_digits=5, decimal_places=1, default=Decimal("0.0")
    )
    balance = models.DecimalField(
        max_digits=5, decimal_places=1, default=Decimal("0.0")
    )

    class Meta:
        db_table = "elm_leave_balance"
        verbose_name_plural = "Leave Balances"
        unique_together = ("user_id", "category", "year")
        indexes = [
            models.Index(fields=["user_id", "year"], name="elm_bal_user_year_idx"),
        ]

    def __str__(self) -> str:
        return f"User {self.user_id} - {self.category.code}: {self.balance}"


class LeaveHistory(models.Model):
    """Audit log of status changes and workflow transitions on a leave application."""

    application = models.ForeignKey(
        LeaveApplication,
        on_delete=models.CASCADE,
        related_name="history",
    )
    actor_id = models.IntegerField()
    action = models.CharField(max_length=50)
    from_status = models.CharField(max_length=30)
    to_status = models.CharField(max_length=30)
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "elm_leave_history"
        verbose_name_plural = "Leave History"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"App {self.application_id}: {self.action} by User {self.actor_id}"
