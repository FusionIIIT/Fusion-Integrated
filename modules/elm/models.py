"""Employee Leave Management (ELM) database models.

Reuses core.db.mixins for consistency with Fusion Base conventions.
"""
from decimal import Decimal
from django.db import models
from core.db.mixins import TimeStampedModel, UserScopedModel


class HolidayCalendar(TimeStampedModel):
    """Annual calendar container maintaining draft vs published state (BR-EL-031, CFR-EL-025)."""
    year = models.PositiveSmallIntegerField(unique=True, db_index=True)
    is_published = models.BooleanField(default=False, db_index=True)
    published_at = models.DateTimeField(null=True, blank=True)
    published_by = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "elm_holiday_calendar"

    def __str__(self) -> str:
        status = "Published" if self.is_published else "Draft"
        return f"Holiday Calendar {self.year} ({status})"


class Holiday(TimeStampedModel):
    """Institute closed holidays and Restricted Holidays (RH)."""
    calendar = models.ForeignKey(HolidayCalendar, on_delete=models.CASCADE, related_name="holidays")
    date = models.DateField(db_index=True)
    name = models.CharField(max_length=120)
    is_rh = models.BooleanField(default=False)      # Restricted Holiday
    is_closed = models.BooleanField(default=True)   # Closed Institute Holiday

    class Meta:
        db_table = "elm_holiday"
        constraints = [
            models.UniqueConstraint(fields=["calendar", "date", "name"], name="elm_holiday_cal_date_name_uniq")
        ]

    def __str__(self) -> str:
        tag = "RH" if self.is_rh else ("Closed" if self.is_closed else "Observance")
        return f"{self.date} - {self.name} [{tag}]"


class LeaveBalance(TimeStampedModel, UserScopedModel):
    """Annual leave entitlement and balance ledger per employee (BR-EL-001..009)."""
    CATEGORY_CHOICES = [
        ("cl", "Casual Leave"),
        ("rh", "Restricted Holiday"),
        ("scl", "Special Casual Leave"),
        ("el", "Earned Leave"),
        ("col", "Commuted Leave"),
        ("vl", "Vacation Leave"),
    ]

    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES)
    year = models.PositiveSmallIntegerField(db_index=True)

    # Multi-bucket ledger
    credited = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal("0.0"))
    carried_forward = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal("0.0"))
    converted_in = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal("0.0"))
    availed = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal("0.0"))
    pending = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal("0.0"))
    converted_out = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal("0.0"))

    class Meta:
        db_table = "elm_leave_balance"
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "category", "year"],
                name="elm_balance_user_cat_year_uniq",
            )
        ]

    @property
    def available(self) -> Decimal:
        """Net available quota ready for new leave applications."""
        total_credit = self.credited + self.carried_forward + self.converted_in
        total_consumed = self.availed + self.pending + self.converted_out
        return total_credit - total_consumed

    def __str__(self) -> str:
        return f"User {self.user_id} - {self.category.upper()} {self.year}: Available {self.available}"


class YearEndProcessingLog(TimeStampedModel):
    """Idempotency log tracking annual rollover and VL-to-EL conversions (BR-EL-007, BR-EL-008)."""
    user_id = models.IntegerField(db_index=True)
    year = models.PositiveSmallIntegerField(db_index=True)
    process_type = models.CharField(max_length=30)  # e.g., 'vl_to_el_conversion'
    vl_converted = models.DecimalField(max_digits=5, decimal_places=1)
    el_credited = models.DecimalField(max_digits=5, decimal_places=1)
    processed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "elm_yearend_processing_log"
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "year", "process_type"],
                name="elm_yearend_user_year_type_uniq",
            )
        ]


class LeaveRequest(TimeStampedModel, UserScopedModel):
    """Leave application with full lifecycle and hierarchy support."""
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("submitted", "Submitted (Legacy)"),
        ("pending_substitute", "Pending Substitute Response"),
        ("substitute_declined", "Substitute Declined"),
        ("pending_unit_head", "Pending Unit Head Review"),
        ("pending_sanction", "Pending Final Sanction"),
        ("awaiting_director_self_sanction", "Awaiting Director Self-Sanction"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("withdrawn", "Withdrawn"),
        ("cancellation_pending_unit_head", "Cancellation Pending Unit Head"),
        ("cancellation_pending_sanction", "Cancellation Pending Final Sanction"),
        ("cancelled", "Cancelled"),
    ]

    CATEGORY_CHOICES = [
        ("cl", "Casual Leave"),
        ("rh", "Restricted Holiday"),
        ("scl", "Special Casual Leave"),
        ("el", "Earned Leave"),
        ("col", "Commuted Leave"),
        ("vl", "Faculty Vacation Leave"),
    ]

    HALF_DAY_CHOICES = [
        ("first_half", "First Half"),
        ("second_half", "Second Half"),
    ]

    SUBSTITUTE_STATUS_CHOICES = [
        ("none", "Not Required"),
        ("pending", "Pending Consent"),
        ("accepted", "Accepted"),
        ("declined", "Declined"),
    ]

    RECOMMENDATION_CHOICES = [
        ("none", "None"),
        ("recommended", "Recommended"),
        ("not_recommended", "Not Recommended"),
    ]

    # Category and Period
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    half_day = models.BooleanField(default=False)
    half_day_type = models.CharField(max_length=16, blank=True, null=True, choices=HALF_DAY_CHOICES)
    leave_days = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    reason = models.TextField()

    # Station Leave Details (BR-EL-013)
    is_station_leave = models.BooleanField(default=False)
    station_address = models.TextField(blank=True, default="")
    station_start_date = models.DateField(null=True, blank=True)
    station_end_date = models.DateField(null=True, blank=True)

    # Substitute Gate (BR-EL-014, BR-EL-015)
    substitute_id = models.IntegerField(null=True, blank=True)
    substitute_status = models.CharField(max_length=16, choices=SUBSTITUTE_STATUS_CHOICES, default="none")
    substitute_remarks = models.TextField(blank=True, default="")

    # Status & Hierarchy (BR-EL-016..020)
    status = models.CharField(max_length=35, choices=STATUS_CHOICES, default="draft", db_index=True)
    unit_head_recommendation = models.CharField(max_length=20, choices=RECOMMENDATION_CHOICES, default="none")
    unit_head_remarks = models.TextField(blank=True, default="")
    sanctioning_remarks = models.TextField(blank=True, default="")

    class Meta:
        db_table = "elm_leaverequest"
        verbose_name = "Leave Request"
        verbose_name_plural = "Leave Requests"
        indexes = [
            models.Index(fields=["user_id", "status"], name="elm_req_user_status_idx"),
            models.Index(fields=["substitute_id", "substitute_status"], name="elm_req_subst_idx"),
        ]

    @property
    def estimated_calendar_interval(self) -> int:
        """Estimated unverified calendar interval for legacy records.
        
        Does not represent verified leave days and is never used for balance adjustments.
        """
        return (self.end_date - self.start_date).days + 1

    def __str__(self) -> str:
        return f"Req #{self.id} - User {self.user_id} - {self.category.upper()} ({self.status})"


class LeaveActionHistory(TimeStampedModel):
    """Immutable audit trail for every workflow transition."""
    leave_request = models.ForeignKey(
        LeaveRequest,
        on_delete=models.PROTECT,   # STRICT: Prevents accidental cascade deletion
        related_name="actions",
    )
    actor_id = models.IntegerField(db_index=True)
    action = models.CharField(max_length=35)
    from_status = models.CharField(max_length=35)
    to_status = models.CharField(max_length=35)
    remarks = models.TextField(blank=True, default="")

    class Meta:
        db_table = "elm_leave_action_history"
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise PermissionError("LeaveActionHistory records are immutable and cannot be updated.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionError("LeaveActionHistory records cannot be deleted.")

    def __str__(self) -> str:
        return f"Action #{self.id} on Req #{self.leave_request_id}: {self.from_status} -> {self.to_status} by {self.actor_id}"
