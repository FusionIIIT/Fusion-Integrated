from django.db import models
from decimal import Decimal
from core.db.mixins import TimeStampedModel


# ---------------------------------------------------------------------------
# Choices
# ---------------------------------------------------------------------------

class LeaveCategory(models.TextChoices):
    CL  = "CL",  "Casual Leave"
    RH  = "RH",  "Restricted Holiday"
    SCL = "SCL", "Special Casual Leave"
    EL  = "EL",  "Earned Leave"
    COL = "COL", "Commuted Leave"
    VL  = "VL",  "Vacation Leave"


class ApplicationStatus(models.TextChoices):
    DRAFT                = "draft",                "Draft"
    PENDING              = "pending",              "Pending"
    AWAITING_SUBSTITUTE  = "awaiting_substitute",  "Awaiting Substitute"
    UNIT_HEAD_REVIEW     = "unit_head_review",     "Unit Head Review"
    PROCESSING           = "processing",           "Processing"
    SANCTIONED           = "sanctioned",           "Sanctioned"
    REJECTED             = "rejected",             "Rejected"
    WITHDRAWN            = "withdrawn",            "Withdrawn"
    CANCELLATION_PENDING = "cancellation_pending", "Cancellation Pending"
    CANCELLED            = "cancelled",            "Cancelled"
    EXTENSION_PENDING    = "extension_pending",    "Extension Pending"


class HolidayKind(models.TextChoices):
    HOLIDAY             = "holiday",             "Holiday"
    RESTRICTED_HOLIDAY  = "restricted_holiday",  "Restricted Holiday"


class ApprovalDecision(models.TextChoices):
    PENDING          = "pending",          "Pending"
    APPROVED         = "approved",         "Approved"
    REJECTED         = "rejected",         "Rejected"
    RECOMMENDED      = "recommended",      "Recommended"
    NOT_RECOMMENDED  = "not_recommended",  "Not Recommended"


class SubstituteStatus(models.TextChoices):
    PENDING  = "pending",  "Pending"
    ACCEPTED = "accepted", "Accepted"
    DECLINED = "declined", "Declined"


class HalfDayChoice(models.TextChoices):
    FIRST  = "first",  "First Half"
    SECOND = "second", "Second Half"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class LeavePolicy(TimeStampedModel):
    year_label    = models.CharField(max_length=20, unique=True)
    cl_days       = models.PositiveSmallIntegerField(default=8)
    rh_days       = models.PositiveSmallIntegerField(default=2)
    scl_days      = models.PositiveSmallIntegerField(default=15)
    el_days       = models.PositiveSmallIntegerField(default=30)
    col_days      = models.PositiveSmallIntegerField(default=15)
    vl_days       = models.PositiveSmallIntegerField(default=30)
    is_published  = models.BooleanField(default=False)

    class Meta:
        db_table = "leave_policy"

    def __str__(self):
        return f"LeavePolicy({self.year_label})"


class HolidayCalendar(TimeStampedModel):
    date         = models.DateField()
    kind         = models.CharField(max_length=30, choices=HolidayKind.choices, default=HolidayKind.HOLIDAY)
    name         = models.CharField(max_length=200)
    is_published = models.BooleanField(default=False)

    class Meta:
        db_table = "leave_holiday_calendar"
        unique_together = [("date", "kind")]

    def __str__(self):
        return f"{self.name} ({self.date})"


class LeaveBalance(TimeStampedModel):
    user_id      = models.IntegerField(db_index=True)
    category     = models.CharField(max_length=10, choices=LeaveCategory.choices)
    balance_days = models.DecimalField(max_digits=6, decimal_places=1, default=Decimal("0.0"))
    year         = models.CharField(max_length=20)

    class Meta:
        db_table = "leave_balance"
        unique_together = [("user_id", "category", "year")]

    def __str__(self):
        return f"u{self.user_id} {self.category}: {self.balance_days} ({self.year})"


class LeaveApplication(TimeStampedModel):
    user_id                = models.IntegerField(db_index=True)
    category               = models.CharField(max_length=10, choices=LeaveCategory.choices)
    start_date             = models.DateField()
    end_date               = models.DateField()
    half_day               = models.BooleanField(default=False)
    half                   = models.CharField(max_length=10, choices=HalfDayChoice.choices, null=True, blank=True)
    station_leave          = models.BooleanField(default=False)
    station_start          = models.DateField(null=True, blank=True)
    station_end            = models.DateField(null=True, blank=True)
    reason                 = models.TextField()
    status                 = models.CharField(max_length=30, choices=ApplicationStatus.choices, default=ApplicationStatus.DRAFT)
    substitute_user_id     = models.IntegerField(null=True, blank=True)
    submitted_at           = models.DateTimeField(null=True, blank=True)
    decided_at             = models.DateTimeField(null=True, blank=True)
    decided_by_user_id     = models.IntegerField(null=True, blank=True)
    unit_head_status       = models.CharField(
        max_length=20, choices=ApprovalDecision.choices,
        default=ApprovalDecision.PENDING, null=True, blank=True
    )
    unit_head_decided_at   = models.DateTimeField(null=True, blank=True)
    final_authority_role   = models.CharField(max_length=100, blank=True)
    is_extension           = models.BooleanField(default=False)
    parent_application     = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="extensions"
    )
    actual_resume_date     = models.DateField(null=True, blank=True)
    withdrawal_reason      = models.TextField(blank=True)
    cancelled_at           = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "leave_application"
        ordering = ["-submitted_at"]

    @property
    def days_requested(self) -> Decimal:
        from modules.leave.domain.rules import count_leave_days
        return count_leave_days(self.start_date, self.end_date, half_day=self.half_day)

    def __str__(self):
        return f"LeaveApp({self.user_id}, {self.category}, {self.start_date}~{self.end_date}, {self.status})"


class ApprovalStep(TimeStampedModel):
    application    = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE, related_name="approval_steps")
    step_order     = models.PositiveSmallIntegerField(default=1)
    authority_role = models.CharField(max_length=100)
    authority_user_id = models.IntegerField(null=True, blank=True)
    decision       = models.CharField(max_length=20, choices=ApprovalDecision.choices, default=ApprovalDecision.PENDING)
    decided_at     = models.DateTimeField(null=True, blank=True)
    comment        = models.TextField(blank=True)

    class Meta:
        db_table = "leave_approval_step"
        ordering = ["step_order"]

    def __str__(self):
        return f"Step({self.application_id}, order={self.step_order}, {self.decision})"


class SubstituteRequest(TimeStampedModel):
    application     = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE, related_name="substitute_requests")
    nominee_user_id = models.IntegerField()
    status          = models.CharField(max_length=10, choices=SubstituteStatus.choices, default=SubstituteStatus.PENDING)
    responded_at    = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "leave_substitute_request"

    def __str__(self):
        return f"SubReq({self.application_id}, nominee={self.nominee_user_id}, {self.status})"


class SlaConfig(models.Model):
    task_class       = models.CharField(max_length=100, unique=True)
    reminder_hours   = models.PositiveIntegerField(default=24)
    escalation_hours = models.PositiveIntegerField(default=48)

    class Meta:
        db_table = "leave_sla_config"

    def __str__(self):
        return f"SLA({self.task_class}, remind={self.reminder_hours}h, escalate={self.escalation_hours}h)"
