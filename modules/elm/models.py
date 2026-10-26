from django.db import models
from django.utils.translation import gettext_lazy as _

from core.db.mixins import TimeStampedModel


class LeaveCategory(models.TextChoices):
    CL = "CL", _("Casual Leave")
    RH = "RH", _("Restricted Holiday")
    SCL = "SCL", _("Special Casual Leave")
    EL = "EL", _("Earned Leave")
    COL = "COL", _("Commuted Leave")
    VL = "VL", _("Vacation Leave")


class LeaveStatus(models.TextChoices):
    DRAFT = "draft", _("Draft")
    SUBMITTED = "submitted", _("Submitted")
    PENDING_SUBSTITUTE = "pending_substitute", _("Pending Substitute")
    PENDING_UNIT_HEAD = "pending_unit_head", _("Pending Unit Head")
    PENDING_SANCTION = "pending_sanction", _("Pending Sanction")
    APPROVED = "approved", _("Approved")
    REJECTED = "rejected", _("Rejected")
    WITHDRAWN = "withdrawn", _("Withdrawn")
    CANCELLATION_REQUESTED = "cancellation_requested", _("Cancellation Requested")
    CANCELLED = "cancelled", _("Cancelled")


class SubstituteStatus(models.TextChoices):
    PENDING = "pending", _("Pending")
    ACCEPTED = "accepted", _("Accepted")
    DECLINED = "declined", _("Declined")


class LeaveBalance(TimeStampedModel):
    user_id = models.IntegerField(db_index=True)
    year = models.PositiveSmallIntegerField(default=2026)
    leave_type = models.CharField(max_length=8, choices=LeaveCategory.choices)
    allocated = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    used = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    balance = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)

    class Meta:
        db_table = "elm_leave_balance"
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "year", "leave_type"],
                name="elm_balance_user_year_type_uniq",
            )
        ]
        indexes = [
            models.Index(fields=["user_id", "year"], name="elm_balance_user_year_idx"),
        ]

    def __str__(self) -> str:
        return f"balance#{self.pk} user={self.user_id} {self.leave_type}:{self.balance}"


class LeaveApplication(TimeStampedModel):
    applicant_id = models.IntegerField(db_index=True)
    leave_type = models.CharField(max_length=8, choices=LeaveCategory.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(blank=True)
    status = models.CharField(
        max_length=24,
        choices=LeaveStatus.choices,
        default=LeaveStatus.SUBMITTED,
    )

    substitute_id = models.IntegerField(null=True, blank=True, db_index=True)
    substitute_status = models.CharField(
        max_length=16,
        choices=SubstituteStatus.choices,
        default=SubstituteStatus.PENDING,
    )

    is_station_leave = models.BooleanField(default=False)
    station_address = models.TextField(blank=True)

    half_day = models.BooleanField(default=False)
    half_day_type = models.CharField(max_length=16, blank=True)

    unit_head_id = models.IntegerField(null=True, blank=True)
    unit_head_recommendation = models.CharField(max_length=24, blank=True)
    sanctioning_authority_id = models.IntegerField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    class Meta:
        db_table = "elm_leave_application"
        indexes = [
            models.Index(fields=["applicant_id", "-created_at"], name="elm_app_applicant_idx"),
            models.Index(fields=["status", "-created_at"], name="elm_app_status_idx"),
            models.Index(fields=["substitute_id", "status"], name="elm_app_substitute_idx"),
        ]

    def __str__(self) -> str:
        return (
            f"leave_app#{self.pk} applicant={self.applicant_id} "
            f"{self.leave_type} ({self.status})"
        )


class LeaveAction(models.Model):
    application = models.ForeignKey(
        LeaveApplication,
        on_delete=models.CASCADE,
        related_name="actions",
    )
    actor_id = models.IntegerField()
    action = models.CharField(max_length=32)
    comments = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "elm_leave_action"
        indexes = [
            models.Index(fields=["application", "-created_at"], name="elm_action_app_idx"),
        ]

    def __str__(self) -> str:
        return f"action#{self.pk} app={self.application_id} {self.action} by={self.actor_id}"
