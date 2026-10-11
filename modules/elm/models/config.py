"""Leave types and the holiday calendar — configured, effective-dated (BR-12).

A leave type is never edited in place: a changed entitlement is a new row with a
later `effective_from`, and the selector resolves the version effective on the
day the request starts.
"""
from django.db import models

from core.db.mixins import TimeStampedModel


class LeaveType(TimeStampedModel):
    """One version of one leave category, effective from a date."""

    code = models.CharField(max_length=12)                 # CL, EL, VL, COL, RH
    name = models.CharField(max_length=60)
    annual_entitlement_days = models.DecimalField(max_digits=5, decimal_places=1,
                                                  default=0)
    #: Working days by default; a calendar-day type counts weekends and holidays.
    counts_calendar_days = models.BooleanField(default=False)
    allows_half_day = models.BooleanField(default=False)
    requires_reason = models.BooleanField(default=False)
    effective_from = models.DateField()
    #: Retiring a version stops offering it; history still resolves through it.
    is_active = models.BooleanField(default=True)
    created_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "elm_leave_type"
        ordering = ["code", "-effective_from"]
        constraints = [
            models.UniqueConstraint(fields=["code", "effective_from"],
                                    name="leave_type_code_effective_unique"),
            models.CheckConstraint(
                condition=models.Q(annual_entitlement_days__gte=0),
                name="leave_type_entitlement_non_negative"),
        ]
        indexes = [
            models.Index(fields=["code", "effective_from"],
                         name="leave_type_lookup_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.code} v{self.effective_from}"


class Holiday(TimeStampedModel):
    """An institute holiday; the day counter excludes these dates."""

    date = models.DateField(unique=True)
    name = models.CharField(max_length=80)
    created_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "elm_holiday"
        ordering = ["date"]

    def __str__(self) -> str:
        return f"{self.date} {self.name}"
