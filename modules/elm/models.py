import uuid
from decimal import Decimal

from django.db import models
from django.db.models import Q
from django.utils import timezone


def current_leave_year() -> int:
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
    PENDING_SUBSTITUTE = "PENDING_SUBSTITUTE", "Pending Substitute Acceptance"
    PENDING_UNIT_HEAD = "PENDING_UNIT_HEAD", "Pending Unit Head Recommendation"
    PENDING_AUTHORITY = "PENDING_AUTHORITY", "Pending Sanctioning Authority"
    APPLICANT_ACTION_REQUIRED = "APPLICANT_ACTION_REQUIRED", "Applicant Action Required"
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
    year = models.PositiveSmallIntegerField(default=current_leave_year)
    credited = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal("0.0"))
    availed = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal("0.0"))
    pending = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal("0.0"))

    class Meta:
        db_table = "elm_leave_balance"
        constraints = [
            models.UniqueConstraint(
                fields=("user_id", "leave_type", "year"),
                name="elm_balance_user_type_year_uniq",
            ),
            models.CheckConstraint(
                condition=Q(credited__gte=0) & Q(availed__gte=0) & Q(pending__gte=0),
                name="elm_balance_values_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(availed__lte=models.F("credited") - models.F("pending")),
                name="elm_balance_usage_within_credit",
            ),
        ]

    def __str__(self):
        return f"{self.user_id} - {self.leave_type}: {self.balance} days"

    @property
    def balance(self) -> Decimal:
        return self.credited - self.availed - self.pending


class LeaveRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    applicant_user_id = models.CharField(max_length=64, db_index=True)
    applicant_role = models.CharField(max_length=64, blank=True, default="")
    leave_type = models.CharField(max_length=8, choices=LeaveType.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    duration_days = models.DecimalField(max_digits=4, decimal_places=1)
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

    # Lifecycle State Machine
    status = models.CharField(
        max_length=32,
        choices=LeaveStatus.choices,
        default=LeaveStatus.DRAFT,
        db_index=True,
    )
    current_approver_role = models.CharField(max_length=64, blank=True, default="unit_head")
    rejection_reason = models.TextField(blank=True, default="")
    unit_head_recommendation = models.CharField(max_length=16, blank=True, default="")

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "elm_leave_request"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(duration_days__gt=0),
                name="elm_leave_duration_positive",
            ),
            models.CheckConstraint(
                condition=(
                    Q(is_half_day=False)
                    | (Q(duration_days=Decimal("0.5")) & Q(start_date=models.F("end_date")))
                ),
                name="elm_half_day_single_day_half_duration",
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
        return f"{self.action} for {self.leave_request_id} by {self.actor_user_id}"
