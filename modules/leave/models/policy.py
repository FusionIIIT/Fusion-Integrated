"""Policy and Calendar models for Employee Leave Management."""

from decimal import Decimal

from django.db import models

from core.db.mixins import TimeStampedModel


class LeaveType(TimeStampedModel):
    """Configurable leave category (BR-EL-001..009, BR-EL-030)."""

    code = models.CharField(max_length=10, unique=True)  # CL, RH, SCL, EL, COL, VL
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_continuous_count = models.BooleanField(default=False)  # BR-EL-011: True for EL, COL, VL
    max_consecutive_days = models.PositiveSmallIntegerField(null=True, blank=True)
    allows_half_day = models.BooleanField(default=False)  # BR-EL-010: True only for CL
    requires_substitute = models.BooleanField(default=False)  # BR-EL-014: Responsibility coverage
    allows_extension = models.BooleanField(default=False)  # BR-EL-025: EL, COL, VL
    carries_forward = models.BooleanField(default=False)  # BR-EL-005: EL, COL
    lapses_at_year_end = models.BooleanField(default=True)  # BR-EL-002: CL, RH, SCL
    requires_medical_certificate = models.BooleanField(default=False)  # BR-EL-009: Commuted Leave
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class CadreLeaveQuota(TimeStampedModel):
    """Standard annual quota by employee cadre (faculty vs staff)."""

    CADRE_CHOICES = [
        ("faculty", "Faculty"),
        ("staff", "Staff"),
    ]
    cadre = models.CharField(max_length=20, choices=CADRE_CHOICES)
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE, related_name="cadre_quotas")
    annual_quota = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal("0.0"))

    class Meta:
        unique_together = ("cadre", "leave_type")

    def __str__(self) -> str:
        return f"{self.cadre}: {self.leave_type.code} = {self.annual_quota}"


class HolidayCalendar(TimeStampedModel):
    """Annual holiday calendar container (BR-EL-031)."""

    year = models.PositiveIntegerField(unique=True)
    title = models.CharField(max_length=120)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"Calendar {self.year} ({'Published' if self.is_published else 'Draft'})"


class Holiday(TimeStampedModel):
    """Institutional holidays (Closed Holidays and Restricted Holidays)."""

    calendar = models.ForeignKey(HolidayCalendar, on_delete=models.CASCADE, related_name="holidays")
    date = models.DateField(db_index=True)
    name = models.CharField(max_length=120)
    is_restricted = models.BooleanField(
        default=False
    )  # True = Restricted Holiday (RH), False = Closed

    class Meta:
        unique_together = ("calendar", "date", "name")

    def __str__(self) -> str:
        kind = "RH" if self.is_restricted else "Closed"
        return f"{self.date} [{kind}]: {self.name}"
