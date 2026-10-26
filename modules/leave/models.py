"""Database models for Employee Leave Management (ELM).

Strict compliance with architectural rules:
- No cross-module ForeignKeys (ADR-0013): user IDs are plain integers.
- Intra-module FKs are allowed (LeaveActionLog -> LeaveApplication).
- Invariants guarded by explicit database CheckConstraints and indexes.
"""

from decimal import Decimal

from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel


class LeaveTypeConfig(TimeStampedModel):
    code = models.CharField(max_length=8, primary_key=True)
    name = models.CharField(max_length=64)
    annual_entitlement = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal("0.0"))
    max_carry_forward = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal("0.0"))
    is_continuous_counting = models.BooleanField(default=False)
    requires_substitute = models.BooleanField(default=True)
    applies_to = models.CharField(max_length=16, default="all")  # all, faculty, staff

    class Meta:
        db_table = "leave_type_config"

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class LeaveBalance(TimeStampedModel):
    user_id = models.IntegerField(db_index=True)
    year = models.PositiveSmallIntegerField(db_index=True)
    leave_type = models.CharField(max_length=8, db_index=True)
    credited = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal("0.0"))
    availed = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal("0.0"))
    balance = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal("0.0"))

    class Meta:
        db_table = "leave_balance"
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "year", "leave_type"],
                name="leave_balance_user_year_type_unique",
            ),
            models.CheckConstraint(
                condition=Q(balance__gte=0),
                name="leave_balance_non_negative",
            ),
        ]
        indexes = [
            models.Index(fields=["user_id", "year"], name="leave_bal_user_year_idx"),
        ]

    def __str__(self) -> str:
        return f"User {self.user_id} {self.leave_type} ({self.year}): {self.balance}"


class HolidayCalendar(TimeStampedModel):
    year = models.PositiveSmallIntegerField(db_index=True)
    date = models.DateField(unique=True)
    name = models.CharField(max_length=120)
    is_restricted_holiday = models.BooleanField(default=False)
    is_closed_holiday = models.BooleanField(default=True)
    is_published = models.BooleanField(default=True)

    class Meta:
        db_table = "leave_holiday_calendar"
        indexes = [
            models.Index(fields=["year", "is_published"], name="leave_holiday_year_pub_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.date}: {self.name} (RH={self.is_restricted_holiday})"


class VacationPeriod(TimeStampedModel):
    year = models.PositiveSmallIntegerField(db_index=True)
    name = models.CharField(max_length=120)
    start_date = models.DateField()
    end_date = models.DateField()
    is_published = models.BooleanField(default=True)

    class Meta:
        db_table = "leave_vacation_period"
        constraints = [
            models.CheckConstraint(
                condition=Q(end_date__gte=models.F("start_date")),
                name="leave_vacation_end_gte_start",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.start_date} to {self.end_date})"


class LeaveApplication(TimeStampedModel):
    STATUS_CHOICES = [
        ("DRAFT", "Draft"),
        ("AWAITING_SUBSTITUTE", "Awaiting Substitute"),
        ("SUBSTITUTE_DECLINED", "Substitute Declined"),
        ("AWAITING_UNIT_HEAD", "Awaiting Unit Head Review"),
        ("AWAITING_ESTABLISHMENT", "Awaiting Establishment Verification"),
        ("AWAITING_SANCTION", "Awaiting Final Sanction"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("WITHDRAWN", "Withdrawn"),
        ("AWAITING_CANCELLATION", "Awaiting Cancellation Review"),
        ("CANCELLED", "Cancelled"),
    ]

    SUBSTITUTE_STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("ACCEPTED", "Accepted"),
        ("DECLINED", "Declined"),
    ]

    applicant_user_id = models.IntegerField(db_index=True)
    leave_type = models.CharField(max_length=8, db_index=True)
    start_date = models.DateField()
    end_date = models.DateField()
    half_day_type = models.CharField(max_length=16, default="FULL")
    days_count = models.DecimalField(max_digits=5, decimal_places=1)
    reason = models.TextField()
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default="DRAFT", db_index=True)

    # Substitute coverage (ACT-02)
    substitute_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    substitute_status = models.CharField(
        max_length=16, choices=SUBSTITUTE_STATUS_CHOICES, default="PENDING"
    )
    substitute_remarks = models.TextField(blank=True)

    # Station Leave (BR-EL-013)
    is_station_leave = models.BooleanField(default=False)
    station_departure_date = models.DateTimeField(null=True, blank=True)
    station_arrival_date = models.DateTimeField(null=True, blank=True)
    station_address = models.TextField(blank=True)
    contact_number = models.CharField(max_length=24, blank=True)

    # Unit Head Review (ACT-03, EL-UC-003)
    unit_head_user_id = models.IntegerField(null=True, blank=True)
    unit_head_recommendation = models.CharField(
        max_length=20, blank=True
    )  # RECOMMENDED, NOT_RECOMMENDED, APPROVED, REJECTED
    unit_head_remarks = models.TextField(blank=True)

    # Establishment Processing (ACT-04, EL-UC-004)
    establishment_remarks = models.TextField(blank=True)

    # Sanctioning Authority Decision (ACT-05/06/07, EL-UC-005)
    sanctioning_authority_user_id = models.IntegerField(null=True, blank=True)
    sanction_decision = models.CharField(max_length=16, blank=True)  # APPROVED, REJECTED
    sanction_remarks = models.TextField(blank=True)

    # Ongoing Extension (EL-UC-009)
    parent_leave_id = models.IntegerField(null=True, blank=True)

    # Cancellation (EL-UC-008)
    is_cancellation_requested = models.BooleanField(default=False)
    cancellation_reason = models.TextField(blank=True)

    # Resumption of Duty (EL-UC-010, EL-UC-011)
    resumption_status = models.CharField(max_length=16, default="NONE")  # NONE, SUBMITTED, REVIEWED
    actual_resumption_date = models.DateField(null=True, blank=True)
    resumption_remarks = models.TextField(blank=True)
    resumption_days_adjusted = models.DecimalField(
        max_digits=5, decimal_places=1, default=Decimal("0.0")
    )

    # Retrospective offline leave (EL-UC-016)
    is_offline = models.BooleanField(default=False)
    offline_sanction_ref = models.CharField(max_length=64, blank=True)
    offline_sanction_date = models.DateField(null=True, blank=True)
    offline_sanctioned_by = models.CharField(max_length=100, blank=True)

    class Meta:
        db_table = "leave_application"
        constraints = [
            models.CheckConstraint(
                condition=Q(end_date__gte=models.F("start_date")),
                name="leave_app_end_gte_start",
            ),
        ]
        indexes = [
            models.Index(fields=["applicant_user_id", "status"], name="leave_app_user_status_idx"),
            models.Index(
                fields=["substitute_user_id", "substitute_status"], name="leave_sub_status_idx"
            ),
            models.Index(fields=["start_date", "end_date"], name="leave_dates_idx"),
        ]

    def __str__(self) -> str:
        return (
            f"Leave #{self.pk} ({self.leave_type}) by User {self.applicant_user_id}: {self.status}"
        )


class LeaveActionLog(TimeStampedModel):
    application = models.ForeignKey(
        LeaveApplication,
        on_delete=models.CASCADE,
        related_name="action_logs",
    )
    actor_user_id = models.IntegerField(db_index=True)
    action = models.CharField(max_length=32)
    from_status = models.CharField(max_length=32)
    to_status = models.CharField(max_length=32)
    remarks = models.TextField(blank=True)

    class Meta:
        db_table = "leave_action_log"
        indexes = [
            models.Index(fields=["application", "created_at"], name="leave_log_app_created_idx"),
        ]

    def __str__(self) -> str:
        return (
            f"Log #{self.pk} on #{self.application_id}: "
            f"{self.action} ({self.from_status} -> {self.to_status})"
        )


class LeaveHierarchyConfig(TimeStampedModel):
    department = models.CharField(max_length=80, unique=True)
    unit_head_user_id = models.IntegerField()
    dr_estt_user_id = models.IntegerField(null=True, blank=True)
    dean_user_id = models.IntegerField(null=True, blank=True)
    registrar_user_id = models.IntegerField(null=True, blank=True)
    director_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "leave_hierarchy_config"

    def __str__(self) -> str:
        return f"Hierarchy for {self.department} (HOD={self.unit_head_user_id})"


class LeaveSLAConfig(TimeStampedModel):
    task_type = models.CharField(max_length=32, unique=True)
    reminder_threshold_hours = models.IntegerField(default=48)
    escalation_threshold_hours = models.IntegerField(default=96)

    class Meta:
        db_table = "leave_sla_config"

    def __str__(self) -> str:
        return (
            f"SLA: {self.task_type} (reminder={self.reminder_threshold_hours}h, "
            f"escalation={self.escalation_threshold_hours}h)"
        )
