"""Database models for Employee Leave Management."""

from django.core.validators import MinValueValidator
from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel


class LeaveType(models.TextChoices):
    CL = "CL", "Casual Leave"
    RH = "RH", "Restricted Holiday"
    SCL = "SCL", "Special Casual Leave"
    EL = "EL", "Earned Leave"
    COL = "COL", "Commuted Leave"
    VL = "VL", "Vacation Leave"


class LeaveApplicationStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    WITHDRAWN = "withdrawn", "Withdrawn"


class LeaveBalance(TimeStampedModel, UserScopedModel):
    """A user's leave balance for a particular leave type and year."""

    leave_type = models.CharField(max_length=3, choices=LeaveType.choices)
    leave_year = models.PositiveSmallIntegerField()
    entitlement = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        validators=[MinValueValidator(0)],
    )
    available_balance = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        validators=[MinValueValidator(0)],
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "leave_type", "leave_year"],
                name="elm_unique_user_leave_year",
            ),
        ]
        indexes = [
            models.Index(
                fields=["user_id", "leave_year"],
                name="elm_user_year_idx",
            ),
        ]

    def __str__(self):
        return (
            f"User {self.user_id}: {self.leave_type} "
            f"{self.leave_year} ({self.available_balance} available)"
        )


class LeaveApplication(TimeStampedModel, UserScopedModel):
    """A leave request submitted by an employee."""

    leave_type = models.CharField(max_length=3, choices=LeaveType.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    half_day = models.CharField(
        max_length=12,
        choices=[
            ("", "Full day"),
            ("first_half", "First half"),
            ("second_half", "Second half"),
        ],
        blank=True,
        default="",
    )

    requested_days = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        validators=[MinValueValidator(0)],
    )
    status = models.CharField(
        max_length=12,
        choices=LeaveApplicationStatus.choices,
        default=LeaveApplicationStatus.PENDING,
        db_index=True,
    )
    reason = models.TextField(blank=True)

    workflow_stage = models.CharField(
        max_length=40,
        default="awaiting_unit_head_review",
        choices=[
            ("awaiting_unit_head_review", "Awaiting Unit Head Review"),
            ("awaiting_establishment", "Awaiting Establishment Routing"),
            ("awaiting_final_sanction", "Awaiting Final Sanction Decision"),
            ("awaiting_director_self_sanction", "Awaiting Director Self-Sanction"),
        ],
    )
    assigned_unit_head_user_id = models.PositiveBigIntegerField(
        null=True,
        blank=True,
    )
    assigned_final_authority_user_id = models.PositiveBigIntegerField(
        null=True,
        blank=True,
    )
    establishment_required = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(
                fields=["user_id", "status"],
                name="elm_user_status_idx",
            ),
            models.Index(
                fields=["user_id", "start_date", "end_date"],
                name="elm_user_dates_idx",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_date__gte=models.F("start_date")),
                name="elm_valid_leave_date_range",
            ),
            models.CheckConstraint(
                condition=models.Q(requested_days__gt=0),
                name="elm_positive_requested_days",
            ),
        ]

    def __str__(self):
        return (
            f"Leave {self.pk}: user {self.user_id}, "
            f"{self.leave_type}, {self.start_date} to {self.end_date}"
        )

    UNIT_HEAD_RECOMMENDATION_CHOICES = [
        ("recommended", "Recommended"),
        ("not_recommended", "Not Recommended"),
    ]

    unit_head_recommendation = models.CharField(
        max_length=20,
        choices=UNIT_HEAD_RECOMMENDATION_CHOICES,
        default="",
        blank=True,
    )

    unit_head_recommendation_remarks = models.TextField(
        blank=True,
    )

    unit_head_recommended_by_user_id = models.PositiveBigIntegerField(
        null=True,
        blank=True,
    )


class YearEndConversion(TimeStampedModel, UserScopedModel):
    """Record a user's VL-to-EL year-end conversion."""

    source_year = models.PositiveSmallIntegerField()
    unused_vl = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        validators=[MinValueValidator(0)],
    )
    converted_el = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        validators=[MinValueValidator(0)],
    )
    applied_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "source_year"],
                name="elm_unique_user_vl_conversion_year",
            ),
        ]

    def __str__(self):
        return (
            f"User {self.user_id}: {self.source_year} VL conversion "
            f"{self.unused_vl} VL -> {self.converted_el} EL"
        )


class LeaveRoutingRule(TimeStampedModel):
    """Configured approval route for an employee and leave category."""

    department = models.CharField(max_length=120)

    applicant_designation = models.CharField(max_length=120)

    leave_type = models.CharField(
        max_length=3,
        choices=LeaveType.choices,
    )

    unit_head_user_id = models.PositiveBigIntegerField(
        null=True,
        blank=True,
    )

    final_authority_user_id = models.PositiveBigIntegerField(
        null=True,
        blank=True,
    )

    establishment_required = models.BooleanField(default=False)

    director_self_sanction = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "department",
                    "applicant_designation",
                    "leave_type",
                ],
                name="elm_unique_routing_context",
            ),
        ]

    def __str__(self):
        return f"{self.department} | {self.applicant_designation} | {self.leave_type}"
