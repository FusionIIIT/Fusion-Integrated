from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from core.db.mixins import TimeStampedModel, UserScopedModel


class LeaveCategory(models.TextChoices):
    CL = "CL", _("Casual Leave")
    RH = "RH", _("Restricted Holiday")
    SCL = "SCL", _("Special Casual Leave")
    EL = "EL", _("Earned Leave")
    COL = "COL", _("Commuted Leave")
    VL = "VL", _("Vacation Leave")


class HalfDaySlot(models.TextChoices):
    NONE = "none", _("Full Day")
    FIRST_HALF = "first_half", _("First Half (Forenoon)")
    SECOND_HALF = "second_half", _("Second Half (Afternoon)")


class LeaveStatus(models.TextChoices):
    DRAFT = "draft", _("Draft")
    SUBMITTED = "submitted", _("Submitted")
    SUBSTITUTE_PENDING = "substitute_pending", _("Pending Substitute Consent")
    UNIT_HEAD_PENDING = "unit_head_pending", _("Pending Unit Head Review")
    SANCTIONING_PENDING = "sanctioning_pending", _("Pending Sanctioning Decision")
    APPROVED = "approved", _("Approved")
    REJECTED = "rejected", _("Rejected")
    WITHDRAWN = "withdrawn", _("Withdrawn")
    CANCELLED = "cancelled", _("Cancelled")
    EXTENDED = "extended", _("Extended")
    RESUMED = "resumed", _("Resumed")


class SubstituteStatus(models.TextChoices):
    NONE = "none", _("Not Applicable")
    PENDING = "pending", _("Pending")
    ACCEPTED = "accepted", _("Accepted")
    DECLINED = "declined", _("Declined")


class UnitHeadRecommendation(models.TextChoices):
    PENDING = "pending", _("Pending")
    RECOMMENDED = "recommended", _("Recommended")
    NOT_RECOMMENDED = "not_recommended", _("Not Recommended")


class LeaveApplication(TimeStampedModel, UserScopedModel):
    category = models.CharField(max_length=4, choices=LeaveCategory.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    half_day_slot = models.CharField(
        max_length=16,
        choices=HalfDaySlot.choices,
        default=HalfDaySlot.NONE,
    )
    calculated_days = models.DecimalField(max_digits=4, decimal_places=1, default=1.0)
    reason = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=24,
        choices=LeaveStatus.choices,
        default=LeaveStatus.DRAFT,
    )

    # Station Leave Coupling (BR-EL-013)
    station_leave_applied = models.BooleanField(default=False)
    station_leave_address = models.CharField(max_length=255, blank=True, default="")
    station_leave_contact = models.CharField(max_length=32, blank=True, default="")
    station_leave_start = models.DateTimeField(null=True, blank=True)
    station_leave_end = models.DateTimeField(null=True, blank=True)

    # Substitute / Responsibility Coverage (BR-EL-014, BR-EL-015)
    substitute_id = models.IntegerField(null=True, blank=True)
    substitute_status = models.CharField(
        max_length=16,
        choices=SubstituteStatus.choices,
        default=SubstituteStatus.NONE,
    )
    substitute_remarks = models.CharField(max_length=255, blank=True, default="")

    # Hierarchical Review & Sanction Routing (BR-EL-016..020)
    unit_head_id = models.IntegerField(null=True, blank=True)
    unit_head_recommendation = models.CharField(
        max_length=20,
        choices=UnitHeadRecommendation.choices,
        default=UnitHeadRecommendation.PENDING,
    )
    unit_head_remarks = models.TextField(blank=True, default="")

    sanctioning_authority_id = models.IntegerField(null=True, blank=True)
    sanctioner_remarks = models.TextField(blank=True, default="")
    decided_at = models.DateTimeField(null=True, blank=True)

    # Cancellation & Resumption Details (BR-EL-023, 027, 028)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True, default="")
    actual_resumption_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "leave_application"
        indexes = [
            models.Index(fields=["user_id", "status"], name="leave_app_user_status_idx"),
            models.Index(fields=["start_date", "end_date"], name="leave_app_dates_idx"),
            models.Index(fields=["substitute_id", "substitute_status"], name="leave_app_sub_idx"),
            models.Index(fields=["unit_head_id", "status"], name="leave_app_uh_idx"),
            models.Index(fields=["sanctioning_authority_id", "status"], name="leave_app_sanc_idx"),
        ]

    def clean(self) -> None:
        super().clean()
        from .domain.rules import validate_leave_application
        validate_leave_application(self)

    def __str__(self) -> str:
        return f"LeaveApp#{self.pk} u{self.user_id} {self.category} ({self.status})"


class LeaveBalance(TimeStampedModel):
    user_id = models.IntegerField(db_index=True)
    year = models.PositiveSmallIntegerField(db_index=True)
    category = models.CharField(max_length=4, choices=LeaveCategory.choices, db_index=True)
    credited = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)
    availed = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)

    class Meta:
        db_table = "leave_balance"
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "year", "category"],
                name="leave_balance_unique_per_user_year_cat",
            ),
        ]
        indexes = [
            models.Index(fields=["user_id", "year"], name="leave_bal_user_year_idx"),
        ]

    @property
    def available_balance(self) -> float:
        return max(0.0, float(self.credited - self.availed))

    def __str__(self) -> str:
        return f"Balance#{self.pk} u{self.user_id} {self.year} {self.category}: {self.available_balance}"


class LeaveApplicationAudit(TimeStampedModel):
    application = models.ForeignKey(
        LeaveApplication,
        on_delete=models.CASCADE,
        related_name="audits",
    )
    actor_id = models.IntegerField(db_index=True)
    action = models.CharField(max_length=32)
    from_status = models.CharField(max_length=24, blank=True, default="")
    to_status = models.CharField(max_length=24)
    remarks = models.TextField(blank=True, default="")

    class Meta:
        db_table = "leave_application_audit"
        indexes = [
            models.Index(fields=["application", "created_at"], name="leave_audit_app_date_idx"),
        ]

    def __str__(self) -> str:
        return f"Audit#{self.pk} App#{self.application_id} {self.action} by u{self.actor_id}"


class HolidayCalendar(TimeStampedModel):
    name = models.CharField(max_length=128)
    date = models.DateField(unique=True)
    is_rh = models.BooleanField(default=False)
    year = models.PositiveSmallIntegerField(db_index=True)

    class Meta:
        db_table = "leave_holiday_calendar"
        ordering = ["date"]

    def __str__(self) -> str:
        return f"{self.date} - {self.name} ({'RH' if self.is_rh else 'Closed Holiday'})"
