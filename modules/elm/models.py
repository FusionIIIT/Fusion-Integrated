"""Employee Leave Management (ELM) models.

These models support all leave categories (CL, RH, SCL, EL, COL, VL) and
Station Leave captured within leave applications, per the v1.4 synchronized
baseline.  They reuse the Fusion ERP time-stamped and user-scoped mixins.
"""

from django.db import models


class LeaveCategory(models.Model):
    """Leave categories supported by ELM baseline."""

    code = models.CharField(max_length=8, unique=True)
    label = models.CharField(max_length=40)
    # Annual entitlement in days (None = configurable)
    annual_entitlement = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    # Whether unused days carry forward year-end
    carry_forward = models.BooleanField(default=False)
    # Whether the continuous-day counting rule applies (EL, COL, VL)
    continuous_day_counting = models.BooleanField(default=False)
    # Leave type: faculty/staff
    applicable_to = models.CharField(
        max_length=1,
        choices=[("F", "Faculty"), ("S", "Staff"), ("B", "Both")],
        default="B",
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
        APPLICANT_ACTION_REQUIRED = "applicant_action_required", "Applicant Action Required"
        WITHDRAWN = "withdrawn", "Withdrawn"
        CANCELLED = "cancelled", "Cancelled"

    class LeaveTypeChoices(models.TextChoices):
        CL = "CL", "Casual Leave"
        RH = "RH", "Restricted Holiday"
        SCL = "SCL", "Special Casual Leave"
        EL = "EL", "Earned Leave"
        COL = "COL", "Commuted Leave"
        VL = "VL", "Vacation Leave"

    class DayPartChoices(models.TextChoices):
        FULL_DAY = "full_day", "Full day"
        FIRST_HALF = "first_half", "First half"
        SECOND_HALF = "second_half", "Second half"

    class CancellationStatus(models.TextChoices):
        NONE = "none", "No cancellation requested"
        PENDING = "pending", "Cancellation pending"
        APPROVED = "approved", "Cancellation approved"
        REJECTED = "rejected", "Cancellation rejected"

    # Core fields
    employee_user_id = models.IntegerField(
        db_index=True,
        help_text="IAM user id of the applicant employee",
    )
    leave_category = models.ForeignKey(
        LeaveCategory,
        on_delete=models.CASCADE,
        help_text="CL, RH, SCL, EL, COL, or VL",
    )
    requested_start = models.DateField(
        help_text="First day of requested leave",
    )
    requested_end = models.DateField(
        help_text="Last day of requested leave (inclusive)",
    )
    day_part = models.CharField(
        max_length=12,
        choices=DayPartChoices.choices,
        default=DayPartChoices.FULL_DAY,
        help_text="CL may use a full or half day; other categories use full days.",
    )
    purpose_reason = models.TextField(
        blank=True,
        help_text="Employee-entered purpose or reason",
    )
    station_leave = models.BooleanField(
        default=False,
        help_text="Whether employee will be outside Jabalpur",
    )
    station_details = models.TextField(
        blank=True,
        help_text="Details if station leave applicable",
    )

    # State tracking
    status = models.CharField(
        max_length=32,
        choices=StatusChoices.choices,
        default=StatusChoices.DRAFT,
    )
    submitted_at = models.DateTimeField(auto_now_add=True)

    # Substitute tracking
    nominated_substitute_user_id = models.IntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text="User id of nominated substitute, if any",
    )
    substitute_accepted = models.BooleanField(
        null=True,
        blank=True,
        help_text="Whether substitute has accepted",
    )
    substitute_decline_reason = models.TextField(
        blank=True,
        help_text="Reason if substitute declined",
    )

    cancellation_status = models.CharField(
        max_length=12,
        choices=CancellationStatus.choices,
        default=CancellationStatus.NONE,
    )
    cancellation_requested_at = models.DateTimeField(null=True, blank=True)
    extension_of = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="extensions",
    )
    actual_resumption_date = models.DateField(null=True, blank=True)
    resumption_details = models.TextField(blank=True)
    resumption_reviewed_at = models.DateTimeField(null=True, blank=True)

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
        db_index=True,
        help_text="IAM user id",
    )
    leave_category = models.ForeignKey(
        LeaveCategory,
        on_delete=models.CASCADE,
        help_text="Associated leave category",
    )
    entitlement_per_year = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text="Annual entitlement granted",
    )
    used_per_year = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text="Days used in current period",
    )
    carried_forward_from_previous = models.DecimalField(
        max_digits=5,
        decimal_places=2,
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
        return (
            f"User {self.user_id} - {self.leave_category.code} ({self.year}): "
            f"{self.available()} available"
        )

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
        LeaveApplication,
        on_delete=models.CASCADE,
        related_name="substitute_nominations",
        help_text="The leave request requiring coverage",
    )
    nominee_user_id = models.IntegerField(
        db_index=True,
        help_text="IAM user id of the nominated employee",
    )
    nominated_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=32,
        choices=StatusChoices.choices,
        default=StatusChoices.PENDING,
    )
    decline_reason = models.TextField(
        blank=True,
        help_text="If declined, reason recorded here",
    )

    class Meta:
        db_table = "elm_substitute_nomination"
        unique_together = ("leave_application", "nominee_user_id")
        indexes = [
            models.Index(fields=["leave_application", "status"]),
        ]

    def __str__(self):
        return (
            f"Sub for ELM-{self.leave_application.pk}: user {self.nominee_user_id} ({self.status})"
        )


class YearEndProcessingRun(models.Model):
    """Idempotency record for a completed year-end account operation."""

    year = models.PositiveSmallIntegerField(unique=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    result = models.JSONField(default=dict)

    class Meta:
        db_table = "elm_year_end_processing_run"
        ordering = ["-year"]

    def __str__(self):
        return f"Year-end processing {self.year}"


class SLAThresholdConfiguration(models.Model):
    """Current configurable reminder and escalation thresholds."""

    class EscalationAction(models.TextChoices):
        NOTIFY = "notify", "Notify only"
        ROUTE_CHANGE = "route_change", "Change routing"
        NONE = "none", "No escalation"

    reminder_threshold_minutes = models.PositiveIntegerField(default=60)
    escalation_threshold_minutes = models.PositiveIntegerField(default=1440)
    escalation_action = models.CharField(
        max_length=20,
        choices=EscalationAction.choices,
        default=EscalationAction.NOTIFY,
    )
    updated_by_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "elm_sla_threshold_configuration"

    def __str__(self):
        return (
            f"SLA thresholds: reminder={self.reminder_threshold_minutes}m, "
            f"escalation={self.escalation_threshold_minutes}m"
        )


class ApprovalRoutingConfiguration(models.Model):
    """Per-category approval roles configured by an ELM administrator.

    Blank roles and an unset establishment choice intentionally block workflow
    routing; the module never assumes a sanctioning authority.
    """

    leave_category = models.OneToOneField(
        LeaveCategory,
        on_delete=models.CASCADE,
        related_name="approval_routing",
    )
    unit_head_role = models.CharField(max_length=120, blank=True)
    establishment_enabled = models.BooleanField(null=True, blank=True)
    establishment_role = models.CharField(max_length=120, blank=True)
    final_authority_role = models.CharField(max_length=120, blank=True)
    updated_by_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "elm_approval_routing_configuration"

    def __str__(self):
        return f"Approval routing for {self.leave_category.code}"

    def is_complete(self):
        if not self.unit_head_role.strip():
            return False
        if self.leave_category.code in {"CL", "RH"}:
            return True
        if self.establishment_enabled is None or not self.final_authority_role.strip():
            return False
        return not self.establishment_enabled or bool(self.establishment_role.strip())


class LeaveApprovalDecision(models.Model):
    """Immutable audit entry for each approval-stage decision."""

    class WorkflowType(models.TextChoices):
        LEAVE = "leave", "Leave sanction"
        CANCELLATION = "cancellation", "Cancellation"

    class Stage(models.TextChoices):
        UNIT_HEAD = "unit_head", "Unit Head"
        ESTABLISHMENT = "establishment", "Establishment"
        FINAL_AUTHORITY = "final_authority", "Final Authority"

    class Outcome(models.TextChoices):
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        RECOMMENDED = "recommended", "Recommended"
        NOT_RECOMMENDED = "not_recommended", "Not Recommended"
        ROUTED = "routed", "Routed"

    application = models.ForeignKey(
        LeaveApplication,
        on_delete=models.CASCADE,
        related_name="approval_decisions",
    )
    workflow_type = models.CharField(
        max_length=16,
        choices=WorkflowType.choices,
        default=WorkflowType.LEAVE,
    )
    stage = models.CharField(max_length=24, choices=Stage.choices)
    outcome = models.CharField(max_length=24, choices=Outcome.choices)
    actor_user_id = models.PositiveBigIntegerField()
    actor_role = models.CharField(max_length=120)
    comments = models.TextField(blank=True)
    decided_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "elm_leave_approval_decision"
        ordering = ["decided_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["application", "workflow_type", "stage"],
                name="elm_one_decision_per_stage",
            )
        ]

    def __str__(self):
        return f"ELM-{self.application_id}: {self.workflow_type} {self.stage} {self.outcome}"
