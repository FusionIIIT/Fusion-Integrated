from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.db.mixins import TimeStampedModel, UserScopedModel

from .domain.rules import is_half_day_cl_valid, is_overlap_valid


class LeaveCategory(models.TextChoices):
    CL = "CL", _("Casual Leave")
    RH = "RH", _("Restricted Holiday")
    SCL = "SCL", _("Special Casual Leave")
    EL = "EL", _("Earned Leave")
    COL = "COL", _("Commuted Leave")
    VL = "VL", _("Vacation Leave")


class LeaveApplication(TimeStampedModel, UserScopedModel):
    STATUS = [
        ("draft", "Draft"),
        ("submitted", "Submitted"),
        ("under_review", "Under Review"),
        ("awaiting_substitute", "Awaiting Substitute Response"),
        ("awaiting_unit_head", "Awaiting Unit Head Review"),
        ("awaiting_sanction", "Awaiting Final Sanction Decision"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("withdrawn", "Withdrawn"),
        ("auto_withdrawn", "Withdrawn Automatically"),
        ("cancelled", "Cancelled"),
        ("ongoing", "Ongoing"),
        ("closed", "Closed"),
    ]

    posting_id = models.IntegerField(default=0, blank=True)
    category = models.CharField(max_length=3, choices=LeaveCategory.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(blank=True)
    half_day_cl = models.BooleanField(default=False)
    station_leave_details = models.JSONField(default=dict, blank=True)
    substitute_id = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=32, choices=STATUS, default="draft")

    def clean(self) -> None:
        super().clean()
        if self.half_day_cl and not is_half_day_cl_valid(
            self.half_day_cl, self.category, self.start_date, self.end_date
        ):
            if self.category != LeaveCategory.CL:
                raise ValidationError({
                    "half_day_cl": _("Half-day leave is only permitted for Casual Leave (CL)."),
                })
            if self.start_date and self.end_date and self.start_date != self.end_date:
                raise ValidationError({
                    "half_day_cl": _("Half-day CL must start and end on the same date."),
                })

        if (
            self.start_date
            and self.end_date
            and not is_overlap_valid(self.start_date, self.end_date)
        ):
            raise ValidationError({
                "start_date": _("Start date must be on or before end date."),
            })

    def __str__(self) -> str:
        return f"app#{self.pk} u{self.user_id} {self.status}"


class LeaveBalance(models.Model):
    user_id = models.IntegerField()
    year = models.PositiveSmallIntegerField()
    balance = models.DecimalField(max_digits=4, decimal_places=2)

    class Meta:
        db_table = "leave_balance"
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "year"],
                name="leave_balance_unique_per_user_year",
            ),
        ]
        indexes = [
            models.Index(fields=["user_id", "year"], name="leave_balance_user_idx"),
        ]

    def __str__(self) -> str:
        return f"balance#{self.pk} u{self.user_id} y{self.year}"

    def clean(self) -> None:
        super().clean()
        if self.balance is not None and self.balance < 0:
            raise ValidationError({
                "balance": _("Leave balance cannot be negative."),
            })



class LeaveApplicationAudit(models.Model):
    application = models.ForeignKey(
        LeaveApplication,
        on_delete=models.CASCADE,
        related_name="audits",
    )
    status = models.CharField(max_length=32)
    reason = models.CharField(max_length=300, blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "leave_application_audit"
        indexes = [
            models.Index(fields=["application", "at"], name="audit_app_idx"),
        ]

    def __str__(self) -> str:
        return f"audit#{self.pk} app#{self.application_id} {self.status}"

