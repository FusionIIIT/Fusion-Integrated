"""Data models for Employee Leave Management (ELM)."""
from decimal import Decimal

from django.db import models
from django.utils import timezone


class LeaveType(models.Model):
    """Categorical definition of an institute leave type."""

    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=128)
    max_days_per_year = models.DecimalField(
        max_digits=5, decimal_places=1, default=Decimal("30.0")
    )
    requires_substitute = models.BooleanField(default=True)
    is_continuous_counting = models.BooleanField(default=False)
    can_carry_forward = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True, default="")

    class Meta:
        db_table = "elm_leave_type"
        ordering = ["code"]

    def __str__(self):
        return f"{self.name} ({self.code})"


class HolidayCalendar(models.Model):
    """Published institute holidays and restricted holidays for calendar year."""

    name = models.CharField(max_length=128)
    date = models.DateField(db_index=True)
    is_restricted = models.BooleanField(default=False)
    year = models.PositiveIntegerField(db_index=True)
    description = models.TextField(blank=True, default="")

    class Meta:
        db_table = "elm_holiday_calendar"
        unique_together = [("date", "name")]
        ordering = ["date"]

    def __str__(self):
        prefix = "RH" if self.is_restricted else "Holiday"
        return f"[{prefix}] {self.name} ({self.date})"


class LeaveBalance(models.Model):
    """Annual leave entitlement and consumption tracking for each employee."""

    employee_id = models.CharField(max_length=64, db_index=True)
    leave_type = models.ForeignKey(
        LeaveType, on_delete=models.CASCADE, related_name="balances"
    )
    year = models.PositiveIntegerField(db_index=True)
    credited = models.DecimalField(
        max_digits=5, decimal_places=1, default=Decimal("0.0")
    )
    consumed = models.DecimalField(
        max_digits=5, decimal_places=1, default=Decimal("0.0")
    )
    carried_forward = models.DecimalField(
        max_digits=5, decimal_places=1, default=Decimal("0.0")
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "elm_leave_balance"
        unique_together = [("employee_id", "leave_type", "year")]
        ordering = ["employee_id", "leave_type__code"]

    def __str__(self):
        return f"{self.employee_id} - {self.leave_type.code}: {self.available} left"

    @property
    def available(self) -> Decimal:
        total = self.credited + self.carried_forward
        return max(Decimal("0.0"), total - self.consumed)


class LeaveApplication(models.Model):
    """Core leave application model capturing workflow states and policy details."""

    STATUS_DRAFT = "DRAFT"
    STATUS_AWAITING_SUBSTITUTE = "AWAITING_SUBSTITUTE"
    STATUS_SUBSTITUTE_DECLINED = "SUBSTITUTE_DECLINED"
    STATUS_AWAITING_UNIT_HEAD = "AWAITING_UNIT_HEAD"
    STATUS_AWAITING_ESTABLISHMENT = "AWAITING_ESTABLISHMENT"
    STATUS_AWAITING_SANCTION = "AWAITING_SANCTION"
    STATUS_AWAITING_DIRECTOR = "AWAITING_DIRECTOR"
    STATUS_APPROVED = "APPROVED"
    STATUS_REJECTED = "REJECTED"
    STATUS_WITHDRAWN = "WITHDRAWN"
    STATUS_CANCELLATION_REQUESTED = "CANCELLATION_REQUESTED"
    STATUS_CANCELLED = "CANCELLED"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_AWAITING_SUBSTITUTE, "Awaiting Substitute Consent"),
        (STATUS_SUBSTITUTE_DECLINED, "Substitute Declined - Action Required"),
        (STATUS_AWAITING_UNIT_HEAD, "Awaiting Unit Head Review"),
        (STATUS_AWAITING_ESTABLISHMENT, "Awaiting Establishment Routing"),
        (STATUS_AWAITING_SANCTION, "Awaiting Sanctioning Authority"),
        (STATUS_AWAITING_DIRECTOR, "Awaiting Director Self-Sanction"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_WITHDRAWN, "Withdrawn"),
        (STATUS_CANCELLATION_REQUESTED, "Cancellation Pending"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    SUB_STATUS_NONE = "NONE"
    SUB_STATUS_PENDING = "PENDING"
    SUB_STATUS_ACCEPTED = "ACCEPTED"
    SUB_STATUS_DECLINED = "DECLINED"
    SUB_STATUS_CHOICES = [
        (SUB_STATUS_NONE, "None Required"),
        (SUB_STATUS_PENDING, "Pending"),
        (SUB_STATUS_ACCEPTED, "Accepted"),
        (SUB_STATUS_DECLINED, "Declined"),
    ]

    RESUMPTION_NONE = "NOT_SUBMITTED"
    RESUMPTION_PENDING = "PENDING"
    RESUMPTION_APPROVED = "APPROVED"
    RESUMPTION_REJECTED = "REJECTED"
    RESUMPTION_CHOICES = [
        (RESUMPTION_NONE, "Not Submitted"),
        (RESUMPTION_PENDING, "Pending Review"),
        (RESUMPTION_APPROVED, "Approved"),
        (RESUMPTION_REJECTED, "Rejected"),
    ]

    applicant_id = models.CharField(max_length=64, db_index=True)
    leave_type = models.ForeignKey(
        LeaveType, on_delete=models.PROTECT, related_name="applications"
    )
    start_date = models.DateField(db_index=True)
    end_date = models.DateField(db_index=True)
    leave_days = models.DecimalField(
        max_digits=5, decimal_places=1, default=Decimal("1.0")
    )
    reason = models.TextField()
    status = models.CharField(
        max_length=32,
        choices=STATUS_CHOICES,
        default=STATUS_AWAITING_UNIT_HEAD,
        db_index=True,
    )

    is_half_day = models.BooleanField(default=False)
    half_day_period = models.CharField(
        max_length=16,
        choices=[("FIRST_HALF", "First Half"), ("SECOND_HALF", "Second Half")],
        blank=True,
        default="",
    )

    station_leave_required = models.BooleanField(default=False)
    departure_date = models.DateField(null=True, blank=True)
    arrival_date = models.DateField(null=True, blank=True)
    station_address = models.TextField(blank=True, default="")
    emergency_contact = models.CharField(max_length=32, blank=True, default="")

    substitute_id = models.CharField(max_length=64, blank=True, default="", db_index=True)
    substitute_status = models.CharField(
        max_length=16, choices=SUB_STATUS_CHOICES, default=SUB_STATUS_NONE
    )
    substitute_remarks = models.TextField(blank=True, default="")
    substitute_responded_at = models.DateTimeField(null=True, blank=True)

    unit_head_id = models.CharField(max_length=64, blank=True, default="")
    unit_head_recommendation = models.CharField(
        max_length=16,
        choices=[("RECOMMENDED", "Recommended"), ("NOT_RECOMMENDED", "Not Recommended")],
        blank=True,
        default="",
    )
    unit_head_remarks = models.TextField(blank=True, default="")
    unit_head_action_at = models.DateTimeField(null=True, blank=True)

    sanctioning_authority_id = models.CharField(max_length=64, blank=True, default="")
    sanction_remarks = models.TextField(blank=True, default="")
    sanctioned_at = models.DateTimeField(null=True, blank=True)

    is_extension = models.BooleanField(default=False)
    parent_application = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="extensions",
    )

    cancellation_reason = models.TextField(blank=True, default="")
    cancellation_requested_at = models.DateTimeField(null=True, blank=True)

    resumption_date = models.DateField(null=True, blank=True)
    resumption_remarks = models.TextField(blank=True, default="")
    resumption_status = models.CharField(
        max_length=16, choices=RESUMPTION_CHOICES, default=RESUMPTION_NONE
    )
    resumption_reviewer_id = models.CharField(max_length=64, blank=True, default="")
    resumption_reviewed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "elm_leave_application"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.applicant_id} - {self.leave_type.code} ({self.status})"


class LeaveWorkflowHistory(models.Model):
    """Audit log of workflow transitions and administrative actions on applications."""

    application = models.ForeignKey(
        LeaveApplication, on_delete=models.CASCADE, related_name="history"
    )
    actor_id = models.CharField(max_length=64, db_index=True)
    action = models.CharField(max_length=64)
    from_state = models.CharField(max_length=32)
    to_state = models.CharField(max_length=32)
    remarks = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "elm_workflow_history"
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.application_id}: {self.action} ({self.from_state}->{self.to_state})"
