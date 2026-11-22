from __future__ import annotations

from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel

CLAIM_STATUS = [
    ("pending_verification", "Awaiting HR verification"),
    ("pending_authority", "Pending current authority"),
    ("pending_next_authority", "Pending next authority"),
    ("approved", "Approved"),
    ("rejected", "Rejected"),
    ("financial_processing_recorded", "Financial processing recorded"),
]

LEAVE_TYPES = [
    ("casual", "Casual"),
    ("restricted", "Restricted"),
    ("medical", "Medical"),
    ("earned", "Earned"),
    ("vacation", "Vacation"),
    ("sabbatical", "Sabbatical"),
]
LEAVE_ROUTE_TYPES = [(f"leave_{code}", f"{label} leave") for code, label in LEAVE_TYPES]
LEAVE_REQUEST_STATUS = [
    ("pending_authority", "Pending current authority"),
    ("pending_next_authority", "Pending next authority"),
    ("approved", "Approved"),
    ("rejected", "Rejected"),
]
CLAIM_REQUEST_TYPES = [
    ("ltc_advance", "LTC advance"),
    ("ltc_reimbursement", "LTC reimbursement"),
    ("cpda_advance", "CPDA advance"),
    ("cpda_reimbursement", "CPDA reimbursement"),
]


class EmployeeRecord(TimeStampedModel):
    CATEGORY = [("faculty", "Faculty"), ("staff", "Staff")]
    EMPLOYMENT_STATUS = [
        ("active", "Active"),
        ("retired", "Retired"),
        ("separated", "Separated"),
    ]

    user_id = models.IntegerField(unique=True)
    employee_category = models.CharField(max_length=16, choices=CATEGORY)
    employment_status = models.CharField(max_length=16, choices=EMPLOYMENT_STATUS, default="active")
    department = models.CharField(max_length=100)
    designation = models.CharField(max_length=100)
    appointment_type = models.CharField(max_length=100, blank=True)
    appointment_start_date = models.DateField(null=True, blank=True)
    appointment_end_date = models.DateField(null=True, blank=True)
    appointment_details = models.JSONField(default=dict, blank=True)
    service_history = models.JSONField(default=list, blank=True)
    retirement_status = models.CharField(max_length=80, blank=True)
    created_by_user_id = models.IntegerField()
    updated_by_user_id = models.IntegerField()

    class Meta:
        db_table = "hr_employee_record"
        indexes = [
            models.Index(
                fields=["employee_category", "department"], name="hr_emp_category_dept_idx"
            ),
            models.Index(fields=["employment_status", "user_id"], name="hr_emp_status_user_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(appointment_end_date__isnull=True)
                    | Q(appointment_start_date__isnull=True)
                    | Q(appointment_end_date__gte=models.F("appointment_start_date"))
                ),
                name="hr_appointment_dates_valid",
            ),
        ]


class LeaveBalance(TimeStampedModel):
    employee = models.ForeignKey(
        EmployeeRecord, on_delete=models.PROTECT, related_name="leave_balances"
    )
    leave_type = models.CharField(max_length=16, choices=LEAVE_TYPES)
    available_days = models.DecimalField(max_digits=8, decimal_places=2)
    is_eligible = models.BooleanField(default=True)
    updated_by_user_id = models.IntegerField()

    class Meta:
        db_table = "hr_leave_balance"
        constraints = [
            models.UniqueConstraint(
                fields=["employee", "leave_type"], name="hr_leave_balance_employee_type_uniq"
            ),
            models.CheckConstraint(
                condition=Q(available_days__gte=0), name="hr_leave_balance_nonnegative"
            ),
        ]
        indexes = [
            models.Index(fields=["leave_type", "is_eligible"], name="hr_leave_type_eligible_idx")
        ]


class WorkflowRoute(TimeStampedModel):
    CATEGORIES = EmployeeRecord.CATEGORY
    REQUEST_TYPES = [*CLAIM_REQUEST_TYPES, *LEAVE_ROUTE_TYPES]

    employee_category = models.CharField(max_length=16, choices=CATEGORIES)
    request_type = models.CharField(max_length=24, choices=REQUEST_TYPES)
    steps = models.JSONField(default=list)
    reminder_after_hours = models.PositiveIntegerField(null=True, blank=True)
    updated_by_user_id = models.IntegerField()

    class Meta:
        db_table = "hr_workflow_route"
        constraints = [
            models.UniqueConstraint(
                fields=["employee_category", "request_type"],
                name="hr_workflow_category_type_uniq",
            ),
        ]


class Claim(TimeStampedModel):
    REQUEST_TYPES = CLAIM_REQUEST_TYPES
    STATUS = CLAIM_STATUS

    employee_user_id = models.IntegerField()
    employee_category = models.CharField(max_length=16, choices=EmployeeRecord.CATEGORY)
    request_type = models.CharField(max_length=24, choices=REQUEST_TYPES)
    purpose = models.CharField(max_length=500, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    form_data = models.JSONField(default=dict, blank=True)
    supporting_documents = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=32, choices=STATUS, default="pending_verification")
    current_authority_user_id = models.IntegerField(null=True, blank=True)
    route_snapshot = models.JSONField(default=list, blank=True)
    authority_step = models.PositiveIntegerField(default=0)
    verification_details = models.JSONField(default=dict, blank=True)
    processing_details = models.JSONField(default=dict, blank=True)
    processed_by_user_id = models.IntegerField(null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "hr_claim"
        indexes = [
            models.Index(
                fields=["employee_user_id", "-created_at"], name="hr_claim_employee_recent_idx"
            ),
            models.Index(
                fields=["status", "current_authority_user_id"], name="hr_claim_authority_status_idx"
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(request_type__in=("cpda_advance", "cpda_reimbursement"), amount__gt=0)
                    | Q(request_type__in=("ltc_advance", "ltc_reimbursement"), amount__isnull=True)
                    | Q(request_type__in=("ltc_advance", "ltc_reimbursement"), amount__gt=0)
                ),
                name="hr_claim_amount_valid",
            ),
            models.CheckConstraint(
                condition=Q(status__in=[code for code, _ in CLAIM_STATUS]),
                name="hr_claim_status_valid",
            ),
        ]


class LeaveRequest(TimeStampedModel):
    STATUS = LEAVE_REQUEST_STATUS

    employee = models.ForeignKey(EmployeeRecord, on_delete=models.PROTECT)
    leave_type = models.CharField(max_length=16, choices=LEAVE_TYPES)
    duration_days = models.DecimalField(max_digits=7, decimal_places=2)
    justification = models.CharField(max_length=1000)
    status = models.CharField(max_length=28, choices=STATUS, default="pending_authority")
    route_snapshot = models.JSONField(default=list)
    authority_step = models.PositiveIntegerField(default=0)
    current_authority_user_id = models.IntegerField(null=True, blank=True)
    submitted_by_user_id = models.IntegerField()

    class Meta:
        db_table = "hr_leave_request"
        constraints = [
            models.CheckConstraint(
                condition=Q(duration_days__gt=0), name="hr_leave_duration_positive"
            ),
            models.CheckConstraint(
                condition=Q(status__in=[code for code, _ in LEAVE_REQUEST_STATUS]),
                name="hr_leave_status_valid",
            ),
        ]
        indexes = [
            models.Index(fields=["employee", "-created_at"], name="hr_leave_employee_recent_idx"),
            models.Index(
                fields=["status", "current_authority_user_id"],
                name="hr_leave_authority_status_idx",
            ),
        ]


class LeaveLedgerQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise TypeError("HR leave ledger entries are immutable.")

    def delete(self):
        raise TypeError("HR leave ledger entries are immutable.")


class LeaveLedgerEntry(models.Model):
    ENTRY_TYPES = [
        ("balance_configured", "Balance configured"),
        ("leave_approved", "Leave approved"),
    ]

    balance = models.ForeignKey(LeaveBalance, on_delete=models.PROTECT, related_name="entries")
    leave_request = models.ForeignKey(
        LeaveRequest, on_delete=models.PROTECT, null=True, blank=True, related_name="ledger_entries"
    )
    entry_type = models.CharField(max_length=24, choices=ENTRY_TYPES)
    amount_delta = models.DecimalField(max_digits=8, decimal_places=2)
    actor_user_id = models.IntegerField()
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = LeaveLedgerQuerySet.as_manager()

    class Meta:
        db_table = "hr_leave_ledger_entry"
        indexes = [
            models.Index(fields=["balance", "created_at"], name="hr_leave_ledger_balance_idx"),
            models.Index(
                fields=["leave_request", "created_at"], name="hr_leave_ledger_request_idx"
            ),
        ]

    def __str__(self):
        return f"{self.entry_type} {self.amount_delta} for balance {self.balance_id}"

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise TypeError("HR leave ledger entries are immutable.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise TypeError("HR leave ledger entries are immutable.")


class ClaimIntegrationStatus(TimeStampedModel):
    SYSTEMS = [("payroll", "Payroll"), ("finance", "Finance")]

    claim = models.ForeignKey(Claim, on_delete=models.PROTECT, related_name="integration_statuses")
    system = models.CharField(max_length=16, choices=SYSTEMS)
    external_status = models.CharField(max_length=100)
    external_reference = models.CharField(max_length=160, blank=True)
    details = models.JSONField(default=dict, blank=True)
    recorded_by_user_id = models.IntegerField()
    received_at = models.DateTimeField()

    class Meta:
        db_table = "hr_claim_integration_status"
        indexes = [
            models.Index(fields=["claim", "-received_at"], name="hr_claim_status_recent_idx"),
        ]


class AppraisalWindow(TimeStampedModel):
    period = models.CharField(max_length=40, unique=True)
    opens_at = models.DateTimeField()
    closes_at = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    updated_by_user_id = models.IntegerField()

    class Meta:
        db_table = "hr_appraisal_window"
        constraints = [
            models.CheckConstraint(
                condition=Q(closes_at__gt=models.F("opens_at")),
                name="hr_appraisal_window_order_valid",
            ),
        ]


class Appraisal(TimeStampedModel):
    STATUS = [
        ("submitted", "Submitted"),
        ("pending_review", "Reviewer assigned / pending review"),
        ("pending_next_authority", "Pending next appraisal authority"),
        ("closed", "Finalized and closed"),
    ]

    employee_user_id = models.IntegerField()
    period = models.CharField(max_length=40)
    form_data = models.JSONField(default=dict)
    status = models.CharField(max_length=28, choices=STATUS, default="submitted")
    reviewer_user_ids = models.JSONField(default=list, blank=True)
    current_reviewer_index = models.PositiveIntegerField(default=0)
    current_reviewer_user_id = models.IntegerField(null=True, blank=True)
    reviews = models.JSONField(default=list, blank=True)
    finalized_at = models.DateTimeField(null=True, blank=True)
    assigned_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "hr_appraisal"
        constraints = [
            models.UniqueConstraint(
                fields=["employee_user_id", "period"],
                name="hr_appraisal_employee_period_uniq",
            ),
            models.CheckConstraint(
                condition=(~Q(status="closed") | Q(finalized_at__isnull=False)),
                name="hr_closed_appraisal_finalized",
            ),
        ]
        indexes = [
            models.Index(
                fields=["employee_user_id", "-created_at"], name="hr_appraisal_employee_idx"
            ),
            models.Index(
                fields=["status", "current_reviewer_user_id"], name="hr_appraisal_reviewer_idx"
            ),
        ]


APPRAISAL_ARCHIVE_TYPE = "appraisal_archive"


class HRNotification(TimeStampedModel):
    EMAIL_STATUS = [
        ("pending", "Pending"),
        ("sending", "Sending"),
        ("sent", "Sent"),
        ("failed", "Failed"),
    ]

    recipient_user_id = models.IntegerField()
    topic = models.CharField(max_length=80)
    dedupe_key = models.CharField(max_length=200, unique=True)
    subject = models.CharField(max_length=160)
    body = models.TextField(max_length=2000)
    payload = models.JSONField(default=dict, blank=True)
    email_status = models.CharField(max_length=12, choices=EMAIL_STATUS, default="pending")
    email_attempts = models.PositiveSmallIntegerField(default=0)
    email_error = models.CharField(max_length=300, blank=True)
    emailed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "hr_notification"
        indexes = [
            models.Index(
                fields=["recipient_user_id", "-created_at"], name="hr_notification_recipient_idx"
            ),
            models.Index(fields=["email_status", "created_at"], name="hr_notification_email_idx"),
        ]


class AuditEventQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise TypeError("HR audit events are immutable.")

    def delete(self):
        raise TypeError("HR audit events are immutable.")


class AuditEvent(TimeStampedModel):
    entity_type = models.CharField(max_length=32)
    entity_id = models.PositiveBigIntegerField()
    actor_user_id = models.IntegerField(null=True, blank=True)
    action = models.CharField(max_length=80)
    details = models.JSONField(default=dict, blank=True)

    objects = AuditEventQuerySet.as_manager()

    class Meta:
        db_table = "hr_audit_event"
        indexes = [
            models.Index(
                fields=["entity_type", "entity_id", "created_at"], name="hr_audit_entity_idx"
            ),
            models.Index(fields=["actor_user_id", "-created_at"], name="hr_audit_actor_idx"),
        ]

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise TypeError("HR audit events are immutable.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise TypeError("HR audit events are immutable.")
