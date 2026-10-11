"""Employee Leave Management (ELM) models.

These models support all leave categories (CL, RH, SCL, EL, COL, VL) and
Station Leave captured within leave applications, per the v1.4 synchronized
baseline.  They reuse the Fusion ERP time-stamped and user-scoped mixins.
"""

from django.db import models
from core.db.mixins import TimeStampedModel, UserScopedModel


class LeaveCategory(models.Model):
    """Leave categories supported by ELM baseline."""
    code = models.CharField(max_length=8, unique = True)
    label = models.CharField(max_length=40)
    # Annual entitlement in days (None = configurable)
    annual_entitlement = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True
    )
    # Whether unused days carry forward year-end
    carry_forward = models.BooleanField(default=False)
    # Whether the continuous-day counting rule applies (EL, COL, VL)
    continuous_day_counting = models.BooleanField(default=False)
    # Leave type: faculty/staff
    applicable_to = models.CharField(
        max_value="F", min_value="S", max_length=1,
        choices=[("F", "Faculty"), ("S", "Staff")],
        default="S",
    )
    # Maximum half-days supported (CL supports half-days)
    supports_half_day = models.BooleanField(default=False)

    class Meta:
        db_table = "elm_leave_category"
        ordering = ["code"]

    def __str__(self):
        return f"{self.code}: {self.label}"


class LeaveApplication(models.Model):
    """A leave application submitted by an employee."""
    class StatusChoices(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        AWAITING_SUBSTITUTE_RESPONSE = "awaiting_substitute_response"
        AWAITING_UNIT_HEAD_REVIEW = "awaiting_unit_head_review"
        AWAITING_ESTABLISHMENT_ROUTING = "awaiting_establishment_routing"
        AWAITING_FINAL_SANCTION = "awaiting_final_sanction"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        WITHDRAWN = "withdrawn", "Withdrawn"
        CANCELLED = "cancelled", "Cancelled"

    class LeaveTypeChoices(models.TextChoices):
        CL = "CL", "Casual Leave"
        RH = "RH", "Restricted Holiday"
        SCL = "SCL", "Special Casual Leave"
        EL = "EL", "Earned Leave"
        COL = "COL", "Commuted Leave"
        VL = "VL", "Vacation Leave"

    # Core fields
    employee_user_id = models.IntegerField(
        db_index=True,
        help_text="IAM user id of the applicant employee",
    )
    leave_category = models.ForeignKey(
        LeaveCategory, on_delete=models.CASCADE,
        help_text="CL, RH, SCL, EL, COL, or VL",
    )
    requested_start = models.DateField(
        help_text="First day of requested leave",
    )
    requested_end = models.DateField(
        help_text="Last day of requested leave (inclusive)",
    )
    purpose_reason = models.TextField(
        blank=True, help_text="Employee-entered purpose or reason",
    )
    station_leave = models.BooleanField(
        default=False,
        help_text="Whether employee will be outside Jabalpur",
    )
    station_details = models.TextField(
        blank=True, help_text="Details if station leave applicable",
    )

    # State tracking
    status = models.CharField(
        max_length=24, choices=StatusChoices.choices,
        default=StatusChoices.DRAFT,
    )
    submitted_at = models.DateTimeField(auto_now_add=True)

    # Substitute tracking
    nominated_substitute_user_id = models.IntegerField(
        null=True, blank=True, db_index=True,
        help_text="User id of nominated substitute, if any",
    )
    substitute_accepted = models.BooleanField(
        null=True, blank=True,
        help_text="Whether substitute has accepted",
    )
    substitute_decline_reason = models.TextField(
        blank=True,
        help_text="Reason if substitute declined",
    )

    class Meta:
        db_table = "elm_leave_application"
        ordering = ["-submitted_at"]
        indexes = [
            models.Index(fields=["employee_user_id", "status"]),
            models.Index(fields=["leave_category", "status"]),
        ]

    def __str__(self):
        return f"ELM-{self.pk}: {self.leave_category.code} by user {self.employee_user_id}"


class LeaveBalance(models.Model):
    """Per-employee per-leave-category balance tracking."""
    user_id = models.IntegerField(
        primary_key=True,
        db_index=True,
        help_text="IAM user id",
    )
    leave_category = models.ForeignKey(
        LeaveCategory, on_delete=models.CASCADE,
        help_text="Associated leave category",
    )
    entitlement_per_year = models.DecimalField(
        max_digits=5, decimal_places=2,
        help_text="Annual entitlement granted",
    )
    used_per_year = models.DecimalField(
        max_digits=5, decimal_places=2,
        default=0,
        help_text="Days used in current period",
    )
    carried_forward_from_previous = models.DecimalField(
        max_digits=5, decimal_places=2,
        default=0,
        help_text="Carried forward from prior year",
    )
    year = models.PositiveSmallIntegerField(
        help_text="Academic/calendar year this balance applies to",
    )

    class Meta:
        db_table = "elm_leave_balance"
        unique_together = ("user_id", "leave_category", "year")
        indexes = [
            models.Index(fields=["user_id", "leave_category"]),
        ]

    def __str__(self):
        return f"User {self.user_id} - {self.leave_category.code} ({self.year}): {self.available()} available"

    def available(self):
        """Return available days = entitlement + carry-forward - used."""
        return self.entitlement_per_year + self.carried_forward_from_previous - self.used_per_year


class SubstituteNomination(models.Model):
    """A substitute nomination for responsibility coverage during leave."""
    class StatusChoices(models.TextChoices):
        PENDING = "pending", "Pending Acceptance"
        ACCEPTED = "accepted", "Accepted"
        DECLINED = "declined", "Declined"
        REPLACEMENT_PENDING = "replacement_pending", "Replacement Pending"

    leave_application = models.ForeignKey(
        LeaveApplication, on_delete=models.CASCADE,
        related_name="substitute_nominations",
        help_text="The leave request requiring coverage",
    )
    nominee_user_id = models.IntegerField(
        db_index=True,
        help_text = "IAM user id of the nominated employee",
    )
    nominated_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=24, choices=StatusChoices.choices,
        default=StatusChoices.PENDING,
    )
    decline_reason = models.TextField(
        blank=True, help_text="If declined, reason recorded here",
    )

    class Meta:
        db_table = "elm_substitute_nomination"
        unique_together = ("leave_application", "nominee_user_id")
        indexes = [
            models.Index(fields=["leave_application", "status"]),
        ]

    def __str__(self):
        return f"Sub for ELM-{self.leave_application.pk}: user {self.nominee_user_id} ({self.status})"
