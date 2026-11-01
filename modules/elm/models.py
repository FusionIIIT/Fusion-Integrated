"""ELM domain models — leave types, balances, applications, and approval flow."""

from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel


# -- Leave Category -----------------------------------------------------------

class LeaveCategory(models.Model):
    """Predefined leave categories configured for the institute."""

    code = models.CharField(max_length=16, unique=True)  # e.g. "CL", "EL", "VL", "COL", "RH", "SCL"
    label = models.CharField(max_length=80)
    entitlement_days = models.PositiveSmallIntegerField(
        help_text="Default annual entitlement per employee",
        default=0
    )
    carry_forward = models.BooleanField(
        default=False,
        help_text="Whether unused days carry to the next year",
    )
    continuous_counting = models.BooleanField(
        default=True,
        help_text="Whether intervening weekends/holidays count as leave days",
    )

    class Meta:
        db_table = "elm_leave_category"
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code}: {self.label}"


# -- Employee Leave Balance / Account -----------------------------------------

class EmployeeLeaveBalance(TimeStampedModel, UserScopedModel):
    """Each employee's remaining entitlement and deducted balance per leave category."""

    leave_category = models.ForeignKey(LeaveCategory, on_delete=models.CASCADE,
                                       related_name="balances")
    # user_id is inherited from UserScopedModel as a plain integer

    remaining_days = models.DecimalField(
        max_digits=5, decimal_places=2,
        help_text="Days still available (may be fractional)"
    )
    used_days = models.DecimalField(
        max_digits=5, decimal_places=2,
        help_text="Days consumed so far this year"
    )

    class Meta:
        db_table = "elm_employee_leave_balance"
        unique_together = ["user_id", "leave_category"]
        ordering = ["user_id", "leave_category"]

    def __str__(self) -> str:
        return f"u{self.user_id} {self.leave_category.code}: {self.remaining_days}"


# -- Leave Application --------------------------------------------------------

class LeaveApplication(TimeStampedModel, UserScopedModel):
    """An employee's request for leave."""

    STATUS = [
        ("submitted", "Submitted"),
        ("unit_head_review", "Unit Head Review"),
        ("recommended", "Recommended"),
        ("not_recommended", "Not Recommended"),
        ("establishment_review", "Establishment Review"),
        ("sanctioned", "Sanctioned"),
        ("rejected", "Rejected"),
        ("withdrawn", "Withdrawn"),
        ("cancelled", "Cancelled"),
    ]

    leave_category = models.ForeignKey(LeaveCategory, on_delete=models.CASCADE,
                                       related_name="applications")
    requested_start = models.DateField()
    requested_end = models.DateField()
    halftype = models.CharField(
        max_length=8, blank=True,
        help_text="FIRST_HALF or SECOND_HALF — for CL half-day support",
    )
    purpose = models.TextField()
    station_leave = models.BooleanField(
        default=False,
        help_text="Whether employee will be outside Jabalpur",
    )
    substitute_nominated = models.IntegerField(
        null=True, blank=True,
        help_text="user_id of nominated substitute, if applicable",
    )
    substitute_accepted = models.BooleanField(
        default=False,
        help_text="Whether the nominated substitute has accepted",
    )

    class Meta:
        db_table = "elm_leave_application"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"app#{self.pk} u{self.user_id} {self.leave_category.code} " \
               f"{self.requested_start}–{self.requested_end}"


# -- Leave Application Transition (audit trail) -----------------------------

class LeaveApplicationTransition(models.Model):
    """Append-only audit of every status change on a leave application."""

    application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE,
                                    related_name="transitions")
    from_status = models.CharField(max_length=32)
    to_status = models.CharField(max_length=32)
    actor_user_id = models.IntegerField(null=True, blank=True)
    actor_label = models.CharField(max_length=80, blank=True)
    reason = models.CharField(max_length=300, blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "elm_leave_application_transition"
        ordering = ["-at"]

    def __str__(self) -> str:
        return f"app#{self.application_id} {self.from_status}->{self.to_status}"


# -- Substitute (for responsibility coverage) -------------------------------

class SubstituteNomination(models.Model):
    """A nominated substitute for responsibility coverage during leave."""

    application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE,
                                    related_name="substitute_nominations")
    substitute_user_id = models.IntegerField()
    nominated_by_user_id = models.IntegerField()  # the applicant
    accepted = models.BooleanField(default=False)
    accepted_at = models.DateTimeField(null=True, blank=True)
    reason = models.CharField(max_length=300, blank=True)

    class Meta:
        db_table = "elm_substitute_nomination"
        unique_together = ["application", "substitute_user_id"]

    def __str__(self) -> str:
        return f"sub#{self.pk} app#{self.application_id} u{self.substitute_user_id}"