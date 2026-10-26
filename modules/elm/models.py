"""Models for the Employee Leave Management (ELM) module."""
from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel


class LeaveType(TimeStampedModel):
    code = models.CharField(max_length=16, unique=True)
    name = models.CharField(max_length=80)
    annual_quota = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    can_carry_forward = models.BooleanField(default=False)
    requires_substitute = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "elm_leave_type"
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class LeaveBalance(TimeStampedModel, UserScopedModel):
    leave_type = models.ForeignKey(
        LeaveType, on_delete=models.PROTECT, related_name="balances"
    )
    year = models.PositiveIntegerField(default=2026)
    allocated = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    used = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    pending = models.DecimalField(max_digits=5, decimal_places=1, default=0)

    class Meta:
        db_table = "elm_leave_balance"
        ordering = ["leave_type__code"]
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "leave_type", "year"],
                name="elm_balance_user_type_year_uniq",
            )
        ]

    @property
    def remaining(self):
        return self.allocated - self.used - self.pending


class LeaveApplication(TimeStampedModel, UserScopedModel):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("awaiting_substitute", "Awaiting Substitute Response"),
        ("applicant_action_required", "Applicant Action Required"),
        ("awaiting_unit_head", "Awaiting Unit Head Review"),
        ("awaiting_final_sanction", "Awaiting Final Sanction Decision"),
        ("awaiting_director", "Awaiting Director Self-Sanction"),
        ("recommended", "Recommended"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("withdrawn", "Withdrawn"),
        ("cancellation_pending_unit_head", "Cancellation Pending — Unit Head Review"),
        ("cancellation_pending_final", "Cancellation Pending — Final Decision"),
        ("cancelled", "Cancelled"),
    ]

    leave_type = models.ForeignKey(
        LeaveType, on_delete=models.PROTECT, related_name="applications"
    )
    start_date = models.DateField()
    end_date = models.DateField()
    half_day = models.BooleanField(default=False)
    station_leave = models.BooleanField(default=False)
    station_address = models.CharField(max_length=255, blank=True)
    reason = models.TextField(blank=True)
    substitute_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    substitute_status = models.CharField(
        max_length=16, default="pending", blank=True
    )
    status = models.CharField(
        max_length=32, choices=STATUS_CHOICES, default="pending", db_index=True
    )
    reviewer_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    review_remarks = models.TextField(blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    # Leave extension (CW-EL-03 / EL-UC-009 / BR-EL-025)
    original_application = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="extensions",
    )
    is_extension = models.BooleanField(default=False)

    # Unit Head recommendation (BR-EL-017)
    recommendation = models.CharField(max_length=32, blank=True, default="")
    recommended_by_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    recommended_at = models.DateTimeField(null=True, blank=True)

    # Cancellation workflow (CW-EL-02 / EL-UC-008 / BR-EL-023)
    cancellation_status = models.CharField(max_length=32, blank=True, default="")
    cancellation_reason = models.TextField(blank=True, default="")
    cancellation_reviewer_user_id = models.IntegerField(
        null=True, blank=True, db_index=True
    )
    cancellation_remarks = models.TextField(blank=True, default="")
    cancellation_decided_at = models.DateTimeField(null=True, blank=True)
    is_balance_refunded = models.BooleanField(default=False)

    # Duty resumption workflow (CW-EL-04 / EL-UC-010 / EL-UC-011 / BR-EL-027, 028)
    actual_resumption_date = models.DateField(null=True, blank=True)
    resumption_status = models.CharField(max_length=32, blank=True, default="")
    resumption_remarks = models.TextField(blank=True, default="")
    resumption_reviewer_user_id = models.IntegerField(
        null=True, blank=True, db_index=True
    )
    resumption_review_remarks = models.TextField(blank=True, default="")
    resumption_decided_at = models.DateTimeField(null=True, blank=True)
    resumption_days_adjusted = models.DecimalField(
        max_digits=5, decimal_places=1, default=0
    )

    # Offline-sanctioned leave (BR-EL-029 / EL-UC-016)
    is_offline = models.BooleanField(default=False)
    sanction_reference = models.CharField(max_length=100, blank=True, default="")
    sanction_date = models.DateField(null=True, blank=True)
    sanction_authority_name = models.CharField(max_length=120, blank=True, default="")

    class Meta:
        db_table = "elm_leave_application"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "sanction_reference"],
                condition=models.Q(is_offline=True) & ~models.Q(sanction_reference=""),
                name="elm_offline_user_sanction_uniq",
            )
        ]

    @property
    def total_days(self):
        days = (self.end_date - self.start_date).days + 1
        return 0.5 if self.half_day and days == 1 else days


class LeaveRolloverRecord(TimeStampedModel):
    user_id = models.IntegerField(db_index=True)
    year = models.PositiveIntegerField()
    cl_lapsed = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    rh_lapsed = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    scl_lapsed = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    vl_converted = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    el_credited_from_vl = models.DecimalField(
        max_digits=5, decimal_places=1, default=0
    )
    el_carried_forward = models.DecimalField(
        max_digits=5, decimal_places=1, default=0
    )
    col_carried_forward = models.DecimalField(
        max_digits=5, decimal_places=1, default=0
    )
    details = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "elm_rollover_record"
        ordering = ["-year", "user_id"]
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "year"],
                name="elm_rollover_user_year_uniq",
            )
        ]

    def __str__(self) -> str:
        return f"Rollover user {self.user_id} year {self.year}"


class HolidayCalendar(TimeStampedModel):
    date = models.DateField(unique=True)
    title = models.CharField(max_length=120)
    is_restricted = models.BooleanField(default=False)

    class Meta:
        db_table = "elm_holiday_calendar"
        ordering = ["date"]

    def __str__(self) -> str:
        return f"{self.date}: {self.title}"
