from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from core.db.mixins import TimeStampedModel, UserScopedModel
from .domain.rules import is_half_day_cl_valid, is_overlap_valid

class LeaveCategory(models.TextChoices):
    CL = "CL", _("Casual Leave")
    RH = "RH", _("Restricted Holiday")
    SCL = "SCL", _("Special Casual Leave")
    EL = "EL", _("Earned Leave")
    COL = "COL", _("Commututed Leave")
    VL = "VL", _("Vacation Leave")

class LeaveApplication(TimeStampedModel, UserScopedModel):
    STATUS = [
        ("draft", "Draft"),
        ("submitted", "Submitted"),
        ("under_review", "Under Review"),
        ("shortlisted", "Shortlisted"),
        ("interview_scheduled", "Interview Scheduled"),
        ("selected", "Selected"),
        ("rejected", "Rejected"),
        ("withdrawn", "Withdrawn"),
        ("auto_withdrawn", "Withdrawn Automatically"),
        ("offer_issued", "Offer Issued"),
        ("offer_accepted", "Offer Accepted"),
        ("offer_declined", "Offer Declined"),
        ("offer_expired", "Offer Expired"),
    ]

    posting_id = models.IntegerField()
    category = models.CharField(max_length=3, choices=LeaveCategory.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(blank=True)
    half_day_cl = models.BooleanField(default=False)
    station_leave_details = models.JSONField(default=dict, blank=True)
    substitute_id = models.IntegerField(null=True)
    status = models.CharField(max_length=24, choices=STATUS, default="draft")

    def clean(self) -> None:
        super().clean()
        if self.category == LeaveCategory.CL:
            if not is_half_day_cl_valid(self.half_day_cl):
                raise ValidationError({
                    "half_day_cl": _("Half-day CL must be valid for this category."),
                })
        if not is_overlap_valid(self.start_date, self.end_date):
            raise ValidationError({
                "start_date": _("Start date must be before end date."),
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
            models.UniqueConstraint(fields=["user_id", "year"],
                                    name="leave_balance_unique_per_user_year"),
        ]
        indexes = [
            models.Index(fields=["user_id", "year"], name="leave_balance_user_idx"),
        ]

    def __str__(self) -> str:
        return f"balance#{self.pk} u{self.user_id} y{self.year}"

class LeaveApplicationAudit(models.Model):
    application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE,
                                    related_name="audits")
    status = models.CharField(max_length=24)
    reason = models.CharField(max_length=300, blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "leave_application_audit"
        indexes = [models.Index(fields=["application", "at"],
                                name="audit_app_idx")]
