from django.db import models

from core.db.mixins import TimeStampedModel


class LeaveApplication(TimeStampedModel):
    LEAVE_CATEGORIES = [
        ("CL", "Casual Leave"),
        ("RH", "Restricted Holiday"),
        ("SCL", "Special Casual Leave"),
        ("EL", "Earned Leave"),
        ("COL", "Commuted Leave"),
        ("VL", "Vacation Leave"),
    ]

    HALF_DAY_CHOICES = [
        ("first_half", "First Half"),
        ("second_half", "Second Half"),
    ]

    SUBSTITUTE_STATUS_CHOICES = [
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("declined", "Declined"),
    ]

    STATUS_CHOICES = [
        ("draft", "Draft / Not Submitted"),
        ("awaiting_substitute", "Awaiting Substitute Response"),
        ("applicant_action_required", "Applicant Action Required"),
        ("awaiting_unit_head", "Awaiting Unit Head Review"),
        ("awaiting_establishment", "Awaiting Establishment Routing"),
        ("awaiting_final_sanction", "Awaiting Final Sanction Decision"),
        ("awaiting_director_self_sanction", "Awaiting Director Self-Sanction"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("withdrawn", "Withdrawn"),
        ("cancelled", "Cancelled"),
        ("cancellation_pending_unit_head", "Cancellation Pending — Unit Head Review"),
        ("cancellation_pending_establishment", "Cancellation Pending — Establishment"),
        ("cancellation_pending_final", "Cancellation Pending — Final Decision"),
        ("awaiting_ext_substitute", "Awaiting Extension Substitute Response"),
        ("ext_applicant_action_required", "Extension Applicant Action Required"),
        ("awaiting_ext_unit_head", "Awaiting Extension Unit Head Review"),
        ("ext_pending_establishment", "Extension Pending — Establishment"),
        ("ext_pending_final", "Extension Pending — Final Decision"),
        ("resumption_review_pending", "Resumption Review Pending"),
        ("resumption_reviewed", "Resumption Reviewed"),
    ]

    # ADR-0013: Plain integer, no cross-module ForeignKey
    user_id = models.IntegerField(db_index=True)
    leave_category = models.CharField(max_length=4, choices=LEAVE_CATEGORIES)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    chargeable_days = models.DecimalField(max_digits=5, decimal_places=1, default=1.0)

    half_day = models.BooleanField(default=False)
    half_day_type = models.CharField(max_length=16, blank=True, choices=HALF_DAY_CHOICES)

    # Station leave fields (BR-EL-013)
    station_leave = models.BooleanField(default=False)
    station_start_date = models.DateField(null=True, blank=True)
    station_end_date = models.DateField(null=True, blank=True)
    station_address = models.TextField(blank=True)
    station_emergency_contact = models.CharField(max_length=32, blank=True)

    # Substitute fields (BR-EL-014, BR-EL-015)
    substitute_required = models.BooleanField(default=False)
    substitute_id = models.IntegerField(null=True, blank=True, db_index=True)
    substitute_status = models.CharField(
        max_length=16, choices=SUBSTITUTE_STATUS_CHOICES, default="pending"
    )
    substitute_remarks = models.TextField(blank=True)

    # Current workflow state
    status = models.CharField(max_length=40, choices=STATUS_CHOICES, default="awaiting_unit_head")

    # Unit head review fields (BR-EL-016, BR-EL-017)
    unit_head_id = models.IntegerField(null=True, blank=True)
    unit_head_recommendation = models.CharField(
        max_length=20,
        blank=True,
        choices=[("recommended", "Recommended"), ("not_recommended", "Not Recommended")],
    )
    unit_head_remarks = models.TextField(blank=True)
    unit_head_acted_at = models.DateTimeField(null=True, blank=True)

    # Sanctioning authority fields (BR-EL-018, BR-EL-020)
    sanctioning_authority_id = models.IntegerField(null=True, blank=True)
    sanction_role = models.CharField(max_length=32, blank=True)
    sanction_decision = models.CharField(
        max_length=16, blank=True, choices=[("approved", "Approved"), ("rejected", "Rejected")]
    )
    sanction_remarks = models.TextField(blank=True)
    sanction_acted_at = models.DateTimeField(null=True, blank=True)

    # Lifecycle, extension & resumption tracking (BR-EL-023..028)
    original_application_id = models.IntegerField(null=True, blank=True, db_index=True)
    resumption_date = models.DateField(null=True, blank=True)
    resumption_reason = models.TextField(blank=True)
    resumption_status = models.CharField(
        max_length=16,
        blank=True,
        choices=[("normal", "Normal"), ("early", "Early"), ("late", "Late")],
    )

    class Meta:
        db_table = "elm_leave_application"
        indexes = [
            models.Index(fields=["user_id", "start_date", "end_date"]),
            models.Index(fields=["status"]),
            models.Index(fields=["substitute_id", "substitute_status"]),
        ]

    def __str__(self):
        return (
            f"User {self.user_id} - {self.get_leave_category_display()} "
            f"({self.start_date} to {self.end_date}): {self.status}"
        )


class LeaveBalance(TimeStampedModel):
    user_id = models.IntegerField(db_index=True)
    year = models.PositiveSmallIntegerField(default=2026)
    leave_category = models.CharField(max_length=4, choices=LeaveApplication.LEAVE_CATEGORIES)
    credited = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)
    used = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)

    class Meta:
        db_table = "elm_leave_balance"
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "year", "leave_category"],
                name="unique_user_year_leave_category",
            )
        ]

    @property
    def available(self):
        return self.credited - self.used

    def __str__(self):
        return f"User {self.user_id} - {self.leave_category} ({self.year}): {self.available} left"


class HolidayCalendar(TimeStampedModel):
    name = models.CharField(max_length=120)
    date = models.DateField(unique=True)
    is_rh = models.BooleanField(default=False)
    is_closed = models.BooleanField(default=True)
    year = models.PositiveSmallIntegerField(default=2026)
    is_published = models.BooleanField(default=True)

    class Meta:
        db_table = "elm_holiday_calendar"
        ordering = ["date"]

    def __str__(self):
        rh_tag = " (RH)" if self.is_rh else ""
        return f"{self.date}: {self.name}{rh_tag}"


class VacationPeriod(TimeStampedModel):
    name = models.CharField(max_length=120)
    start_date = models.DateField()
    end_date = models.DateField()
    year = models.PositiveSmallIntegerField(default=2026)

    class Meta:
        db_table = "elm_vacation_period"
        ordering = ["start_date"]

    def __str__(self):
        return f"{self.name} ({self.start_date} to {self.end_date})"


class OfflineLeaveRecord(TimeStampedModel):
    user_id = models.IntegerField(db_index=True)
    leave_category = models.CharField(max_length=4, choices=LeaveApplication.LEAVE_CATEGORIES)
    start_date = models.DateField()
    end_date = models.DateField()
    chargeable_days = models.DecimalField(max_digits=5, decimal_places=1)
    sanction_reference = models.CharField(max_length=120)
    evidence_notes = models.TextField(blank=True)
    recorded_by_id = models.IntegerField()

    class Meta:
        db_table = "elm_offline_leave_record"

    def __str__(self):
        return f"Offline {self.leave_category} for User {self.user_id} ({self.sanction_reference})"
