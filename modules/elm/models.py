import uuid
from decimal import Decimal

from django.db import models
from django.utils import timezone


def current_year():
    return timezone.localdate().year


class LeaveType(models.TextChoices):
    CASUAL = "CL", "Casual Leave"
    RESTRICTED = "RH", "Restricted Holiday"
    SPECIAL_CASUAL = "SCL", "Special Casual Leave"
    EARNED = "EL", "Earned Leave"
    COMMUTED = "COL", "Commuted Leave"
    VACATION = "VL", "Vacation Leave"


class LeaveStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    APPLICANT_ACTION = "APPLICANT_ACTION", "Replacement Substitute Required"
    PENDING_SUBSTITUTE = "PENDING_SUBSTITUTE", "Pending Substitute Acceptance"
    PENDING_UNIT_HEAD = "PENDING_UNIT_HEAD", "Pending Unit Head Recommendation"
    PENDING_AUTHORITY = "PENDING_AUTHORITY", "Pending Sanctioning Authority"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    WITHDRAWN = "WITHDRAWN", "Withdrawn by Applicant"
    CANCELLED = "CANCELLED", "Cancelled"


class SubstituteStatus(models.TextChoices):
    NOT_REQUIRED = "NOT_REQUIRED", "Not Required"
    PENDING = "PENDING", "Pending Response"
    ACCEPTED = "ACCEPTED", "Accepted"
    REJECTED = "REJECTED", "Declined"


class LeaveBalance(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.CharField(max_length=64, db_index=True)
    leave_type = models.CharField(max_length=8, choices=LeaveType.choices)
    year = models.PositiveSmallIntegerField(default=current_year)
    credited = models.DecimalField(max_digits=9, decimal_places=2, default=Decimal("0.0"))
    availed = models.DecimalField(max_digits=9, decimal_places=2, default=Decimal("0.0"))
    pending = models.DecimalField(max_digits=9, decimal_places=2, default=Decimal("0.0"))

    closed = models.BooleanField(default=False)

    class Meta:
        db_table = "elm_leave_balance"
        unique_together = ("user_id", "leave_type", "year")
        constraints = [
            models.CheckConstraint(
                condition=models.Q(credited__gte=0, availed__gte=0, pending__gte=0),
                name="elm_nonnegative_ledger",
            ),
            models.CheckConstraint(
                condition=models.Q(credited__gte=models.F("availed") + models.F("pending")),
                name="elm_balance_not_overdrawn",
            ),
        ]

    def __str__(self):
        return f"{self.user_id} - {self.leave_type}: {self.balance} days"

    @property
    def balance(self) -> Decimal:
        return Decimal(0) if self.closed else self.credited - self.availed - self.pending


class LeaveRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    applicant_user_id = models.CharField(max_length=64, db_index=True)
    leave_type = models.CharField(max_length=8, choices=LeaveType.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    duration_days = models.DecimalField(max_digits=9, decimal_places=2)
    is_half_day = models.BooleanField(default=False)
    half_day_session = models.CharField(max_length=4, blank=True, default="")
    reason = models.TextField()

    # Station Leave Coupling (SRS-EL-004 & SRS-EL-005)
    station_leave = models.BooleanField(default=False)
    station_leave_address = models.TextField(blank=True, default="")
    out_of_station_from = models.DateField(null=True, blank=True)
    out_of_station_to = models.DateField(null=True, blank=True)

    # Substitute Responsibility (Actor/Role Registry)
    substitute_user_id = models.CharField(max_length=64, blank=True, default="", db_index=True)
    substitute_status = models.CharField(
        max_length=16,
        choices=SubstituteStatus.choices,
        default=SubstituteStatus.NOT_REQUIRED,
    )
    substitute_remarks = models.TextField(blank=True, default="")

    request_kind = models.CharField(max_length=12, default="LEAVE")
    original = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="followups"
    )
    route = models.JSONField(default=list)
    route_index = models.PositiveSmallIntegerField(default=0)
    current_approver_user_id = models.CharField(
        max_length=64, blank=True, default="", db_index=True
    )
    recommendation = models.CharField(max_length=24, blank=True, default="")
    evidence_reference = models.TextField(blank=True, default="")
    actual_end_date = models.DateField(null=True, blank=True)
    actual_duration_days = models.DecimalField(
        max_digits=9, decimal_places=2, null=True, blank=True
    )
    task_assigned_at = models.DateTimeField(default=timezone.now)
    reminder_sent = models.BooleanField(default=False)
    escalation_sent = models.BooleanField(default=False)

    # Lifecycle State Machine
    status = models.CharField(
        max_length=32,
        choices=LeaveStatus.choices,
        default=LeaveStatus.DRAFT,
        db_index=True,
    )
    current_approver_role = models.CharField(max_length=64, blank=True, default="unit_head")
    rejection_reason = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "elm_leave_request"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(duration_days__gt=0), name="elm_positive_duration"
            ),
            models.CheckConstraint(
                condition=models.Q(end_date__gte=models.F("start_date")), name="elm_ordered_dates"
            ),
        ]

    def __str__(self):
        return f"Leave {self.id} ({self.applicant_user_id} - {self.leave_type} - {self.status})"


class LeaveActionLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    leave_request = models.ForeignKey(
        LeaveRequest,
        on_delete=models.CASCADE,
        related_name="action_logs",
    )
    actor_user_id = models.CharField(max_length=64)
    actor_role = models.CharField(max_length=64)
    action = models.CharField(max_length=32)
    remarks = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "elm_action_log"
        ordering = ["created_at"]

    def __str__(self):
        return f"LeaveActionLog {self.pk}"


class EmployeeRecord(models.Model):
    """ELM policy/routing data; identity still belongs to Fusion IAM."""

    user_id = models.CharField(max_length=64, primary_key=True)
    kind = models.CharField(max_length=8, choices=[("faculty", "Faculty"), ("staff", "Staff")])
    unit = models.CharField(max_length=128)
    designation = models.CharField(max_length=128)
    is_director = models.BooleanField(default=False)
    coverage_required = models.BooleanField(default=False)
    col_eligible = models.BooleanField(default=True)
    routes = models.JSONField(default=dict)
    escalation_user_id = models.CharField(max_length=64, blank=True, default="")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"EmployeeRecord {self.pk}"


class LeavePolicy(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1)
    annual_credits = models.JSONField(default=dict, blank=True)
    weekend_days = models.JSONField(default=list, blank=True)
    medical_evidence_required = models.BooleanField(default=False)
    reminder_hours = models.PositiveIntegerField(default=24)
    escalation_hours = models.PositiveIntegerField(default=48)

    def __str__(self):
        return f"LeavePolicy {self.pk}"


class HolidayCalendar(models.Model):
    year = models.PositiveSmallIntegerField()
    closed_dates = models.JSONField(default=list)
    restricted_dates = models.JSONField(default=list)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"HolidayCalendar {self.pk}"


class VacationPeriod(models.Model):
    """Read-only projection of vacation periods supplied by the Academic Calendar."""

    source_reference = models.CharField(max_length=256)
    start_date = models.DateField()
    end_date = models.DateField()

    def __str__(self):
        return f"VacationPeriod {self.pk}"


class AccountEntry(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_id = models.CharField(max_length=64, db_index=True)
    leave_type = models.CharField(max_length=8)
    year = models.PositiveSmallIntegerField()
    action = models.CharField(max_length=32)
    amount = models.DecimalField(max_digits=9, decimal_places=2)
    request = models.ForeignKey(LeaveRequest, null=True, on_delete=models.PROTECT)
    actor_user_id = models.CharField(max_length=64)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"AccountEntry {self.pk}"


class Notification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient_user_id = models.CharField(max_length=64, db_index=True)
    request = models.ForeignKey(LeaveRequest, on_delete=models.PROTECT)
    event = models.CharField(max_length=32)
    message = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Notification {self.pk}"


class AttendanceEvent(models.Model):
    """Durable integration outbox; consumers acknowledge after synchronizing attendance."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    request = models.ForeignKey(LeaveRequest, on_delete=models.PROTECT)
    user_id = models.CharField(max_length=64)
    event = models.CharField(max_length=32)
    payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(default=timezone.now)
    delivered_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"AttendanceEvent {self.pk}"


class ConfigurationAudit(models.Model):
    actor_user_id = models.CharField(max_length=64)
    resource = models.CharField(max_length=128)
    payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"ConfigurationAudit {self.pk}"
