"""ELM-owned policy, workflow, and account records.

People are referenced by IAM user_id values; this module never creates a user table.
"""

from decimal import Decimal

from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel


class LeaveCategory(TimeStampedModel):
    CODES = [
        ("CL", "Casual Leave"),
        ("RH", "Restricted Holiday"),
        ("SCL", "Special Casual Leave"),
        ("EL", "Earned Leave"),
        ("COL", "Commuted Leave"),
        ("VL", "Vacation Leave"),
    ]
    EMPLOYEE_SCOPE = [
        ("all", "All employees"),
        ("faculty", "Faculty only"),
        ("staff", "Staff only"),
    ]
    COUNTING_RULES = [
        ("continuous", "Continuous calendar days"),
        ("working_days", "Working days"),
        ("calendar_days", "Calendar days"),
    ]

    code = models.CharField(max_length=8, choices=CODES, unique=True)
    name = models.CharField(max_length=80)
    annual_entitlement = models.DecimalField(max_digits=7, decimal_places=2)
    employee_scope = models.CharField(max_length=12, choices=EMPLOYEE_SCOPE, default="all")
    carry_forward = models.BooleanField(default=False)
    counting_rule = models.CharField(max_length=16, choices=COUNTING_RULES)
    requires_medical_evidence = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "elm_leave_category"
        ordering = ["code"]

    def __str__(self):
        return self.code


class EmployeeContext(TimeStampedModel):
    """ELM-specific organizational context, not a duplicate identity record."""

    EMPLOYEE_KINDS = [("faculty", "Faculty"), ("staff", "Staff")]

    user_id = models.IntegerField(unique=True)
    employee_kind = models.CharField(max_length=12, choices=EMPLOYEE_KINDS)
    designation = models.CharField(max_length=120)
    organizational_unit = models.CharField(max_length=120)
    unit_head_user_id = models.IntegerField(null=True, blank=True)
    is_director = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "elm_employee_context"
        indexes = [
            models.Index(
                fields=["organizational_unit", "designation"], name="elm_employee_route_idx"
            )
        ]


class ApprovalRoute(TimeStampedModel):
    """Current hierarchy rule. Blank match fields act as less-specific fallbacks."""

    employee_kind = models.CharField(max_length=12, choices=EmployeeContext.EMPLOYEE_KINDS)
    organizational_unit = models.CharField(max_length=120, blank=True)
    designation = models.CharField(max_length=120, blank=True)
    category = models.CharField(max_length=8, choices=LeaveCategory.CODES)
    final_authority_user_id = models.IntegerField()
    final_authority_role = models.CharField(max_length=80)
    establishment_user_id = models.IntegerField(null=True, blank=True)
    establishment_required = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "elm_approval_route"
        constraints = [
            models.UniqueConstraint(
                fields=["employee_kind", "organizational_unit", "designation", "category"],
                name="elm_route_context_unique",
            ),
        ]


class HolidayCalendar(TimeStampedModel):
    name = models.CharField(max_length=120)
    is_published = models.BooleanField(default=False, db_index=True)
    published_at = models.DateTimeField(null=True, blank=True)
    created_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "elm_holiday_calendar"
        constraints = [
            models.UniqueConstraint(
                fields=["is_published"],
                condition=Q(is_published=True),
                name="elm_one_effective_calendar",
            ),
        ]


class CalendarEntry(TimeStampedModel):
    KINDS = [("closed", "Closed holiday"), ("restricted", "Restricted holiday")]

    calendar = models.ForeignKey(HolidayCalendar, on_delete=models.CASCADE, related_name="entries")
    day = models.DateField()
    kind = models.CharField(max_length=12, choices=KINDS)
    name = models.CharField(max_length=160)

    class Meta:
        db_table = "elm_calendar_entry"
        constraints = [
            models.UniqueConstraint(
                fields=["calendar", "day", "kind"], name="elm_calendar_day_kind_unique"
            ),
        ]
        indexes = [models.Index(fields=["calendar", "day"], name="elm_calendar_date_idx")]


class VacationPeriod(TimeStampedModel):
    """Vacation dates imported from the external Academic Calendar service."""

    name = models.CharField(max_length=120)
    starts_on = models.DateField()
    ends_on = models.DateField()
    source_reference = models.CharField(max_length=240, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "elm_vacation_period"
        constraints = [
            models.CheckConstraint(
                condition=Q(ends_on__gte=models.F("starts_on")), name="elm_vacation_dates_valid"
            ),
        ]


class LeaveAccount(TimeStampedModel):
    user_id = models.IntegerField(db_index=True)
    category = models.ForeignKey(LeaveCategory, on_delete=models.PROTECT)
    year = models.PositiveSmallIntegerField()
    annual_entitlement = models.DecimalField(max_digits=7, decimal_places=2)
    opening_balance = models.DecimalField(max_digits=7, decimal_places=2, default=Decimal("0"))

    class Meta:
        db_table = "elm_leave_account"
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "category", "year"], name="elm_account_user_category_year_unique"
            ),
        ]
        indexes = [models.Index(fields=["user_id", "year"], name="elm_account_user_year_idx")]


class LeaveRequest(TimeStampedModel):
    REQUEST_TYPES = [
        ("new", "New leave"),
        ("extension", "Extension"),
        ("cancellation", "Cancellation"),
        ("offline", "Offline-synchronized leave"),
    ]
    STATUSES = [
        ("awaiting_substitute", "Awaiting substitute"),
        ("applicant_action_required", "Applicant action required"),
        ("awaiting_unit_head", "Awaiting Unit Head"),
        ("awaiting_establishment", "Awaiting Establishment"),
        ("awaiting_final", "Awaiting final authority"),
        ("awaiting_director", "Awaiting Director self-sanction"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("withdrawn", "Withdrawn"),
        ("cancelled", "Cancelled"),
    ]
    HALF_DAYS = [("", "Full day"), ("first", "First half"), ("second", "Second half")]
    SUBSTITUTE_RESPONSES = [
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("declined", "Declined"),
    ]

    employee_user_id = models.IntegerField(db_index=True)
    category = models.ForeignKey(LeaveCategory, on_delete=models.PROTECT)
    request_type = models.CharField(max_length=16, choices=REQUEST_TYPES, default="new")
    status = models.CharField(max_length=32, choices=STATUSES, db_index=True)
    starts_on = models.DateField()
    ends_on = models.DateField()
    chargeable_days = models.DecimalField(max_digits=7, decimal_places=2)
    half_day = models.CharField(max_length=8, choices=HALF_DAYS, blank=True)
    reason = models.TextField()
    station_leave = models.BooleanField(default=False)
    station_leave_details = models.CharField(max_length=500, blank=True)
    substitute_required = models.BooleanField(default=False)
    substitute_user_id = models.IntegerField(null=True, blank=True)
    substitute_response = models.CharField(
        max_length=12, choices=SUBSTITUTE_RESPONSES, default="pending"
    )
    evidence_reference = models.CharField(max_length=500, blank=True)
    original_leave = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="related_requests"
    )
    route_snapshot = models.JSONField(default=dict, blank=True)
    final_decision_by_user_id = models.IntegerField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    offline_sanction_reference = models.CharField(max_length=240, blank=True)

    class Meta:
        db_table = "elm_leave_request"
        indexes = [
            models.Index(
                fields=["employee_user_id", "-created_at"], name="elm_request_employee_idx"
            ),
            models.Index(fields=["status", "created_at"], name="elm_request_status_idx"),
            models.Index(fields=["category", "starts_on", "ends_on"], name="elm_request_dates_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(ends_on__gte=models.F("starts_on")), name="elm_request_dates_valid"
            ),
            models.CheckConstraint(
                condition=~Q(request_type="extension") | Q(original_leave__isnull=False),
                name="elm_extension_has_original",
            ),
            models.CheckConstraint(
                condition=~Q(request_type="cancellation") | Q(original_leave__isnull=False),
                name="elm_cancellation_has_original",
            ),
            models.UniqueConstraint(
                fields=["offline_sanction_reference"],
                condition=Q(request_type="offline") & ~Q(offline_sanction_reference=""),
                name="elm_offline_reference_unique",
            ),
        ]


class LeaveReservation(TimeStampedModel):
    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE, related_name="reservations")
    account = models.ForeignKey(LeaveAccount, on_delete=models.PROTECT, related_name="reservations")
    amount = models.DecimalField(max_digits=7, decimal_places=2)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "elm_leave_reservation"
        constraints = [
            models.UniqueConstraint(
                fields=["request", "account"], name="elm_request_account_reservation_unique"
            ),
        ]


class LeaveTransaction(models.Model):
    KINDS = [
        ("credit", "Annual or carry-forward credit"),
        ("charge", "Approved leave charge"),
        ("reversal", "Approved cancellation or adjustment"),
        ("lapse", "Year-end lapse"),
        ("conversion", "VL to EL conversion"),
        ("offline", "Offline-synchronized leave"),
        ("admin_adjustment", "Authorized record correction"),
        ("resumption_adjustment", "Resumption review adjustment"),
    ]

    account = models.ForeignKey(LeaveAccount, on_delete=models.PROTECT, related_name="transactions")
    request = models.ForeignKey(
        LeaveRequest, null=True, blank=True, on_delete=models.PROTECT, related_name="transactions"
    )
    kind = models.CharField(max_length=24, choices=KINDS)
    amount = models.DecimalField(max_digits=7, decimal_places=2)
    reference = models.CharField(max_length=240, blank=True)
    note = models.TextField(blank=True)
    actor_user_id = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "elm_leave_transaction"
        indexes = [
            models.Index(fields=["account", "created_at"], name="elm_transaction_account_idx")
        ]

    def __str__(self):
        return f"{self.account_id}:{self.kind}:{self.amount}"


class WorkflowTask(TimeStampedModel):
    TASK_TYPES = [
        ("substitute", "Substitute response"),
        ("unit_head", "Unit Head review"),
        ("establishment", "Establishment routing"),
        ("final", "Final decision"),
        ("resumption", "Resumption review"),
    ]
    STATES = [("pending", "Pending"), ("completed", "Completed"), ("cancelled", "Cancelled")]

    request = models.ForeignKey(
        LeaveRequest, null=True, blank=True, on_delete=models.CASCADE, related_name="tasks"
    )
    task_type = models.CharField(max_length=20, choices=TASK_TYPES)
    assigned_to_user_id = models.IntegerField(db_index=True)
    status = models.CharField(max_length=12, choices=STATES, default="pending", db_index=True)
    assigned_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    reminded_at = models.DateTimeField(null=True, blank=True)
    escalated_at = models.DateTimeField(null=True, blank=True)
    escalation_user_id = models.IntegerField(null=True, blank=True)
    reminder_after_hours = models.PositiveIntegerField(null=True, blank=True)
    escalation_after_hours = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        db_table = "elm_workflow_task"
        indexes = [
            models.Index(
                fields=["assigned_to_user_id", "status"], name="elm_task_assignee_status_idx"
            ),
            models.Index(fields=["status", "assigned_at"], name="elm_task_pending_idx"),
        ]


class LeaveEvent(models.Model):
    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE, related_name="events")
    from_status = models.CharField(max_length=32, blank=True)
    to_status = models.CharField(max_length=32)
    event_type = models.CharField(max_length=32)
    actor_user_id = models.IntegerField(null=True, blank=True)
    actor_role = models.CharField(max_length=80, blank=True)
    note = models.TextField(blank=True)
    data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "elm_leave_event"
        ordering = ["created_at", "id"]

    def __str__(self):
        return f"{self.request_id}:{self.event_type}"


class ResumptionRecord(TimeStampedModel):
    STATES = [("pending", "Pending review"), ("reviewed", "Reviewed")]

    leave = models.ForeignKey(LeaveRequest, on_delete=models.PROTECT, related_name="resumptions")
    employee_user_id = models.IntegerField(db_index=True)
    actual_return_date = models.DateField()
    details = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=STATES, default="pending")
    reviewer_user_id = models.IntegerField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    adjustment_days = models.DecimalField(max_digits=7, decimal_places=2, default=Decimal("0"))

    class Meta:
        db_table = "elm_resumption_record"
        constraints = [
            models.UniqueConstraint(
                fields=["leave"], condition=Q(status="pending"), name="elm_one_pending_resumption"
            ),
        ]


class ELMNotification(models.Model):
    user_id = models.IntegerField(db_index=True)
    request = models.ForeignKey(
        LeaveRequest, null=True, blank=True, on_delete=models.CASCADE, related_name="notifications"
    )
    kind = models.CharField(max_length=32)
    title = models.CharField(max_length=180)
    body = models.CharField(max_length=500)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "elm_notification"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class SLAConfiguration(TimeStampedModel):
    task_type = models.CharField(max_length=20, choices=WorkflowTask.TASK_TYPES, unique=True)
    reminder_after_hours = models.PositiveIntegerField()
    escalation_after_hours = models.PositiveIntegerField()
    escalation_user_id = models.IntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "elm_sla_configuration"


class YearEndRun(models.Model):
    STATES = [("running", "Running"), ("completed", "Completed"), ("failed", "Failed")]

    year = models.PositiveSmallIntegerField(unique=True)
    status = models.CharField(max_length=12, choices=STATES, default="running")
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    summary = models.JSONField(default=dict, blank=True)
    exceptions = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = "elm_year_end_run"

    def __str__(self):
        return f"{self.year} ({self.status})"


class AdminAuditEvent(models.Model):
    """Append-only audit trail for policy and account administration."""

    actor_user_id = models.IntegerField(db_index=True)
    target_type = models.CharField(max_length=40)
    target_id = models.PositiveBigIntegerField()
    event_type = models.CharField(max_length=32)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "elm_admin_audit_event"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["target_type", "target_id", "created_at"], name="elm_admin_audit_target_idx"
            )
        ]

    def __str__(self):
        return f"{self.target_type}:{self.target_id}:{self.event_type}"
