"""Models for Employee Leave Management (ELM).

Strict compliance with Fusion architecture:
- No foreign key crosses a module boundary (enforced by ops/checks/no_cross_module_fk.py).
- user_id is a plain integer index.
"""
from decimal import Decimal
from django.db import models
from core.db.mixins import TimeStampedModel
from modules.leave.domain.constants import (
    HalfDayOption,
    LeaveCategory,
    LeaveStatus,
    SubstituteStatus,
    UnitHeadDecision,
)

CATEGORY_CHOICES = [(c.value, c.name) for c in LeaveCategory]
HALF_DAY_CHOICES = [(h.value, h.name) for h in HalfDayOption]
STATUS_CHOICES = [(s.value, s.name) for s in LeaveStatus]
SUBSTITUTE_STATUS_CHOICES = [(ss.value, ss.name) for ss in SubstituteStatus]


class LeaveBalance(TimeStampedModel):
    """Annual leave balance ledger per employee and leave category."""

    user_id = models.IntegerField(db_index=True)
    year = models.PositiveSmallIntegerField(db_index=True)
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES, db_index=True)
    credited = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal("0.0"))
    availed = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal("0.0"))
    balance = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal("0.0"))

    class Meta:
        db_table = "leave_balances"
        unique_together = ("user_id", "year", "category")
        indexes = [
            models.Index(fields=["user_id", "year"]),
        ]

    def __str__(self) -> str:
        return f"User {self.user_id} - {self.category} ({self.year}): {self.balance} left"


class LeaveRequest(TimeStampedModel):
    """Core leave application model capturing lifecycle, approvals, and embedded station leave."""

    user_id = models.IntegerField(db_index=True)
    category = models.CharField(max_length=10, choices=CATEGORY_CHOICES, db_index=True)
    start_date = models.DateField(db_index=True)
    end_date = models.DateField(db_index=True)
    half_day = models.CharField(max_length=15, choices=HALF_DAY_CHOICES, default=HalfDayOption.NONE.value)
    computed_days = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal("1.0"))
    reason = models.TextField()
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default=LeaveStatus.PENDING_UNIT_HEAD.value,
        db_index=True,
    )

    # Substitute Gate (BR-EL-014, BR-EL-015)
    substitute_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    substitute_status = models.CharField(
        max_length=20,
        choices=SUBSTITUTE_STATUS_CHOICES,
        default=SubstituteStatus.NOT_REQUIRED.value,
    )
    substitute_remarks = models.TextField(blank=True)

    # Station Leave Coupling (BR-EL-013)
    station_leave = models.BooleanField(default=False)
    station_address = models.CharField(max_length=255, blank=True)
    station_contact = models.CharField(max_length=50, blank=True)
    station_start_date = models.DateField(null=True, blank=True)
    station_end_date = models.DateField(null=True, blank=True)

    # Medical Certificate / Document URL (BR-EL-009)
    medical_certificate_url = models.CharField(max_length=500, blank=True)

    # Unit Head Review (BR-EL-016, BR-EL-017)
    unit_head_user_id = models.IntegerField(null=True, blank=True)
    unit_head_recommendation = models.CharField(max_length=20, blank=True)
    unit_head_remarks = models.TextField(blank=True)

    # Higher Sanction Decision (BR-EL-018, BR-EL-019, BR-EL-020)
    sanctioning_authority_user_id = models.IntegerField(null=True, blank=True)
    sanction_remarks = models.TextField(blank=True)

    # Offline Sanction Synchronization (BR-EL-029)
    offline_entry = models.BooleanField(default=False)
    offline_reference = models.CharField(max_length=100, blank=True)

    # Cancellation Request (BR-EL-023, BR-EL-024)
    cancellation_reason = models.TextField(blank=True)

    # Extension Request (BR-EL-025)
    extension_base_request_id = models.IntegerField(null=True, blank=True)
    extension_days = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal("0.0"))

    # Resumption of Duty (BR-EL-027, BR-EL-028)
    resumption_date = models.DateField(null=True, blank=True)
    resumption_remarks = models.TextField(blank=True)
    resumption_status = models.CharField(max_length=20, blank=True)

    class Meta:
        db_table = "leave_requests"
        indexes = [
            models.Index(fields=["user_id", "status"]),
            models.Index(fields=["substitute_user_id", "substitute_status"]),
            models.Index(fields=["start_date", "end_date"]),
        ]

    def __str__(self) -> str:
        return f"LeaveRequest #{self.id} (User {self.user_id}, {self.category}, {self.status})"


class LeaveActionLog(TimeStampedModel):
    """Immutable audit trail of actions and transitions for leave applications."""

    leave_request_id = models.IntegerField(db_index=True)
    actor_user_id = models.IntegerField(db_index=True)
    action = models.CharField(max_length=40)
    from_status = models.CharField(max_length=30)
    to_status = models.CharField(max_length=30)
    remarks = models.TextField(blank=True)

    class Meta:
        db_table = "leave_action_logs"
        ordering = ["created_at"]


class HolidayCalendar(TimeStampedModel):
    """Published institute holiday and restricted holiday calendar (BR-EL-031)."""

    date = models.DateField(unique=True, db_index=True)
    name = models.CharField(max_length=100)
    is_restricted = models.BooleanField(default=False)
    year = models.PositiveSmallIntegerField(db_index=True)
    published = models.BooleanField(default=True)

    class Meta:
        db_table = "leave_holiday_calendar"
        ordering = ["date"]

    def __str__(self) -> str:
        kind = "RH" if self.is_restricted else "Closed Holiday"
        return f"{self.date}: {self.name} ({kind})"


class VacationPeriod(TimeStampedModel):
    """Vacation periods provided by the institute Academic Calendar (BR-EL-006)."""

    name = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    year = models.PositiveSmallIntegerField(db_index=True)

    class Meta:
        db_table = "leave_vacation_periods"
        ordering = ["start_date"]

    def __str__(self) -> str:
        return f"{self.name} ({self.start_date} to {self.end_date})"


class LeavePolicyConfig(TimeStampedModel):
    """Configurable leave policy parameters (BR-EL-030)."""

    category = models.CharField(max_length=10, unique=True, choices=CATEGORY_CHOICES)
    annual_entitlement = models.DecimalField(max_digits=5, decimal_places=1)
    carries_forward = models.BooleanField(default=False)
    max_carry_forward = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    continuous_counting = models.BooleanField(default=False)

    class Meta:
        db_table = "leave_policy_configs"


class SLAConfig(TimeStampedModel):
    """SLA reminder and escalation thresholds (BR-EL-038)."""

    task_type = models.CharField(max_length=40, unique=True)
    reminder_hours = models.PositiveIntegerField(default=48)
    escalation_hours = models.PositiveIntegerField(default=96)
    escalation_target_role = models.CharField(max_length=50, blank=True)

    class Meta:
        db_table = "leave_sla_configs"
