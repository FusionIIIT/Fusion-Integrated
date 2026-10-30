"""Leave module database tables.

Cross-module references are plain user_id integers, never foreign keys.
"""
from decimal import Decimal
from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel
from .domain.constants import (
    ALL_LEAVE_CATEGORIES,
    HALF_DAY_FIRST,
    HALF_DAY_FULL,
    HALF_DAY_SECOND,
    STATUS_DRAFT,
    SUBSTITUTE_NOT_REQUIRED,
)


class LeaveCategory(models.TextChoices):
    CL = "CL", "Casual Leave"
    RH = "RH", "Restricted Holiday"
    SCL = "SCL", "Special Casual Leave"
    EL = "EL", "Earned Leave"
    COL = "COL", "Commuted Leave"
    VL = "VL", "Vacation Leave"


class HalfDayChoice(models.TextChoices):
    FULL = HALF_DAY_FULL, "Full Day"
    FIRST_HALF = HALF_DAY_FIRST, "First Half"
    SECOND_HALF = HALF_DAY_SECOND, "Second Half"


class LeaveBalance(TimeStampedModel, UserScopedModel):
    """Annual leave entitlement and balance tracking (BR-EL-002 to BR-EL-009)."""

    year = models.PositiveSmallIntegerField(default=2026, db_index=True)
    category = models.CharField(max_length=8, choices=LeaveCategory.choices)
    credited = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal("0.0"))
    availed = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal("0.0"))
    balance = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal("0.0"))
    lapsed = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal("0.0"))

    class Meta:
        db_table = "leave_balance"
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "year", "category"],
                name="leave_balance_user_year_cat_uniq",
            )
        ]

    def __str__(self) -> str:
        return f"User {self.user_id} - {self.category} ({self.year}): bal={self.balance}"


class HolidayCalendar(TimeStampedModel):
    """Institute calendar: closed holidays, restricted holidays, and vacation periods (BR-EL-031)."""

    date = models.DateField(unique=True)
    name = models.CharField(max_length=120)
    is_restricted_holiday = models.BooleanField(default=False)
    is_closed_holiday = models.BooleanField(default=False)
    is_vacation_period = models.BooleanField(default=False)
    year = models.PositiveSmallIntegerField(db_index=True)

    class Meta:
        db_table = "leave_holiday_calendar"
        indexes = [
            models.Index(fields=["year", "is_restricted_holiday"], name="leave_cal_rh_idx"),
            models.Index(fields=["year", "is_vacation_period"], name="leave_cal_vac_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.date}: {self.name}"


class LeaveRequest(TimeStampedModel, UserScopedModel):
    """Leave application and full approval lifecycle state (WF-EL-01 to WF-EL-05)."""

    category = models.CharField(max_length=8, choices=LeaveCategory.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    half_day = models.CharField(
        max_length=16, choices=HalfDayChoice.choices, default=HalfDayChoice.FULL
    )
    requested_days = models.DecimalField(max_digits=4, decimal_places=1)
    purpose = models.TextField()
    status = models.CharField(max_length=38, default=STATUS_DRAFT, db_index=True)

    # Station Leave coupled information (SRS-EL-004, SRS-EL-005, BR-EL-013)
    station_leave = models.BooleanField(default=False)
    station_start_date = models.DateField(null=True, blank=True)
    station_end_date = models.DateField(null=True, blank=True)
    station_address = models.CharField(max_length=255, blank=True)
    station_contact = models.CharField(max_length=32, blank=True)

    # Substitute Nomination & Consent (BR-EL-014, BR-EL-015)
    substitute_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    substitute_status = models.CharField(max_length=16, default=SUBSTITUTE_NOT_REQUIRED)
    substitute_remarks = models.CharField(max_length=255, blank=True)

    # Unit Head Review (BR-EL-016, BR-EL-017)
    unit_head_user_id = models.IntegerField(null=True, blank=True)
    unit_head_decision = models.CharField(max_length=20, blank=True)
    unit_head_remarks = models.TextField(blank=True)

    # Final Sanctioning Decision (BR-EL-018, BR-EL-020)
    sanctioning_authority_user_id = models.IntegerField(null=True, blank=True)
    sanctioning_decision = models.CharField(max_length=20, blank=True)
    sanctioning_remarks = models.TextField(blank=True)

    # Extension & Resumption (BR-EL-025, BR-EL-027, BR-EL-028)
    parent_leave_id = models.IntegerField(null=True, blank=True, db_index=True)
    actual_resumption_date = models.DateField(null=True, blank=True)
    resumption_verified = models.BooleanField(default=False)
    restored_days = models.DecimalField(max_digits=4, decimal_places=1, default=Decimal("0.0"))

    # Offline-Sanctioned Leave (BR-EL-029, SRS-EL-094)
    is_offline = models.BooleanField(default=False)
    offline_reference = models.CharField(max_length=100, blank=True)

    class Meta:
        db_table = "leave_request"
        indexes = [
            models.Index(fields=["user_id", "status"], name="leave_req_user_status_idx"),
            models.Index(fields=["start_date", "end_date"], name="leave_req_dates_idx"),
        ]

    def __str__(self) -> str:
        return f"LeaveRequest {self.pk} ({self.category} {self.start_date}..{self.end_date}) [{self.status}]"
