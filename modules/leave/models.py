"""Persistence for the Employee Leave Management domain.

Employee identities are local IAM references (integer IDs), never cross-module
foreign keys. Balances are projections of an immutable account ledger.
"""
from django.db import models
from django.db.models import Q


class EmployeeProfile(models.Model):
    """Current employee facts and routing context projected from HR/IAM."""

    class Kind(models.TextChoices):
        FACULTY = "faculty", "Faculty"
        STAFF = "staff", "Staff"

    user_id = models.PositiveBigIntegerField(primary_key=True)
    kind = models.CharField(max_length=8, choices=Kind.choices)
    designation = models.CharField(max_length=120)
    unit_code = models.CharField(max_length=64, db_index=True)
    unit_head_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    is_director = models.BooleanField(default=False)
    active = models.BooleanField(default=True)
    synced_at = models.DateTimeField()

    class Meta:
        db_table = "leave_employee_profile"


class LeaveCategory(models.Model):
    code = models.CharField(max_length=3, primary_key=True)
    label = models.CharField(max_length=64)
    description = models.TextField(blank=True)
    class Meta:
        db_table = "leave_category"
        ordering = ["code"]


class LeavePolicy(models.Model):
    """Current configurable parameters; policy versions are not part of ELM."""

    policy_key = models.CharField(max_length=16, primary_key=True, default="current", editable=False)
    cl_days = models.DecimalField(max_digits=6, decimal_places=2, default=8)
    rh_days = models.DecimalField(max_digits=6, decimal_places=2, default=2)
    scl_days = models.DecimalField(max_digits=6, decimal_places=2, default=15)
    faculty_vl_days = models.DecimalField(max_digits=6, decimal_places=2, default=60)
    nonfaculty_el_days = models.DecimalField(max_digits=6, decimal_places=2, default=30)
    col_days = models.DecimalField(max_digits=6, decimal_places=2, default=20)
    col_medical_evidence_required = models.BooleanField(default=False)
    year_end_month = models.PositiveSmallIntegerField(default=12)
    year_end_day = models.PositiveSmallIntegerField(default=31)
    updated_by_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "leave_policy"


class LeaveBalance(models.Model):
    """Materialized balance, reconciled to its immutable ledger entries."""

    employee_id = models.PositiveBigIntegerField(db_index=True)
    category = models.ForeignKey(LeaveCategory, on_delete=models.PROTECT, related_name="balances")
    year = models.PositiveSmallIntegerField()
    entitlement = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    carried_over = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    available = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "leave_balance"
        constraints = [models.UniqueConstraint(fields=["employee_id", "category", "year"], name="leave_balance_employee_category_year_uniq")]
        indexes = [models.Index(fields=["employee_id", "year"], name="leave_balance_employee_year_idx")]


class LeaveRequest(models.Model):
    """Immutable-after-submission request; follow-on actions are separate records."""

    class Type(models.TextChoices):
        NEW = "new", "New leave"
        CANCELLATION = "cancellation", "Cancellation"
        EXTENSION = "extension", "Extension"
        RESUMPTION = "resumption", "Resumption"
        OFFLINE = "offline", "Offline sanctioned entry"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        AWAITING_SUBSTITUTE = "awaiting_substitute", "Awaiting substitute"
        APPLICANT_ACTION = "applicant_action", "Applicant action required"
        PENDING_UNIT_HEAD = "pending_unit_head", "Pending Unit Head"
        PENDING_ESTABLISHMENT = "pending_establishment", "Pending Establishment"
        PENDING_AUTHORITY = "pending_authority", "Pending authority"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        WITHDRAWN = "withdrawn", "Withdrawn"
        CANCELLED = "cancelled", "Cancelled"
        COMPLETED = "completed", "Completed"

    class CLPortion(models.TextChoices):
        FULL = "full", "Full day"
        FIRST_HALF = "first_half", "First half"
        SECOND_HALF = "second_half", "Second half"

    employee_id = models.PositiveBigIntegerField(db_index=True)
    category = models.ForeignKey(LeaveCategory, on_delete=models.PROTECT, related_name="requests")
    request_type = models.CharField(max_length=16, choices=Type.choices, default=Type.NEW)
    parent_request = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="follow_ups")
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.DRAFT, db_index=True)
    start_date = models.DateField()
    end_date = models.DateField()
    duration_days = models.DecimalField(max_digits=7, decimal_places=2)
    cl_portion = models.CharField(max_length=16, choices=CLPortion.choices, default=CLPortion.FULL)
    reason = models.TextField()
    station_leave = models.BooleanField(default=False)
    station_destination = models.CharField(max_length=240, blank=True)
    station_departure_at = models.DateTimeField(null=True, blank=True)
    station_return_at = models.DateTimeField(null=True, blank=True)
    medical_evidence_ref = models.CharField(max_length=500, blank=True)
    substitute_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    actual_resume_date = models.DateField(null=True, blank=True)
    offline_sanction_ref = models.CharField(max_length=240, blank=True)
    offline_evidence_ref = models.CharField(max_length=500, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "leave_request"
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["employee_id", "status"], name="leave_request_employee_status_idx"), models.Index(fields=["start_date", "end_date", "status"], name="leave_request_period_status_idx")]
        constraints = [models.CheckConstraint(condition=Q(end_date__gte=models.F("start_date")), name="leave_request_valid_date_range")]


class SubstituteResponse(models.Model):
    class Decision(models.TextChoices):
        ACCEPTED = "accepted", "Accepted"
        DECLINED = "declined", "Declined"

    request = models.ForeignKey(LeaveRequest, on_delete=models.PROTECT, related_name="substitute_responses")
    substitute_user_id = models.PositiveBigIntegerField()
    decision = models.CharField(max_length=12, choices=Decision.choices)
    responded_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = "leave_substitute_response"
        ordering = ["-responded_at"]


class WorkflowTask(models.Model):
    """Assigned decision/review step; each response is recorded as a sanction."""

    class State(models.TextChoices):
        QUEUED = "queued", "Queued"
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    request = models.ForeignKey(LeaveRequest, on_delete=models.PROTECT, related_name="tasks")
    sequence = models.PositiveSmallIntegerField()
    role = models.CharField(max_length=64)
    decision_kind = models.CharField(max_length=20, choices=[("final", "Final decision"), ("recommendation", "Recommendation"), ("forward", "Forward")])
    assigned_user_id = models.PositiveBigIntegerField(null=True, blank=True, db_index=True)
    state = models.CharField(max_length=12, choices=State.choices, default=State.PENDING, db_index=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    due_at = models.DateTimeField(null=True, blank=True)
    reminder_sent_at = models.DateTimeField(null=True, blank=True)
    escalated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = "leave_workflow_task"
        ordering = ["sequence", "id"]
        constraints = [models.UniqueConstraint(fields=["request", "sequence"], name="leave_workflow_request_sequence_uniq")]
        indexes = [models.Index(fields=["state", "due_at"], name="leave_task_state_due_idx")]


class LeaveSanction(models.Model):
    class Decision(models.TextChoices):
        RECOMMENDED = "recommended", "Recommended"
        NOT_RECOMMENDED = "not_recommended", "Not recommended"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        FORWARDED = "forwarded", "Forwarded"

    task = models.OneToOneField(WorkflowTask, on_delete=models.PROTECT, related_name="sanction")
    actor_user_id = models.PositiveBigIntegerField()
    decision = models.CharField(max_length=20, choices=Decision.choices)
    notes = models.TextField(blank=True)
    decided_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = "leave_sanction"
        ordering = ["decided_at"]


class LeaveAccountEntry(models.Model):
    """Append-only credits/debits; positive amounts credit, negative debit."""

    class Kind(models.TextChoices):
        ENTITLEMENT = "entitlement", "Entitlement"
        CARRY_FORWARD = "carry_forward", "Carry forward"
        LEAVE_USED = "leave_used", "Leave used"
        CANCELLATION_REVERSAL = "cancellation_reversal", "Cancellation reversal"
        VL_CONVERSION = "vl_conversion", "VL to EL conversion"
        RESUMPTION_ADJUSTMENT = "resumption_adjustment", "Resumption adjustment"
        OFFLINE_ADJUSTMENT = "offline_adjustment", "Offline adjustment"
        YEAR_END_LAPSE = "year_end_lapse", "Year-end lapse"

    employee_id = models.PositiveBigIntegerField(db_index=True)
    category = models.ForeignKey(LeaveCategory, on_delete=models.PROTECT, related_name="entries")
    year = models.PositiveSmallIntegerField()
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    kind = models.CharField(max_length=32, choices=Kind.choices)
    request = models.ForeignKey(LeaveRequest, null=True, blank=True, on_delete=models.PROTECT, related_name="account_entries")
    source_key = models.CharField(max_length=120, unique=True)
    actor_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    explanation = models.CharField(max_length=240, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = "leave_account_entry"
        ordering = ["created_at", "id"]
        indexes = [models.Index(fields=["employee_id", "category", "year"], name="leave_entry_account_idx")]


class HolidayCalendar(models.Model):
    class State(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        SUPERSEDED = "superseded", "Superseded"

    year = models.PositiveSmallIntegerField()
    revision = models.PositiveSmallIntegerField(default=1)
    holidays = models.JSONField(default=list)
    state = models.CharField(max_length=12, choices=State.choices, default=State.DRAFT)
    published_by_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = "leave_holiday_calendar"
        constraints = [models.UniqueConstraint(fields=["year", "revision"], name="leave_calendar_year_revision_uniq")]
        indexes = [models.Index(fields=["year", "state"], name="leave_calendar_year_state_idx")]


class VacationPeriod(models.Model):
    """Read-only projection of vacation dates from the external Academic Calendar."""
    external_id = models.CharField(max_length=120, unique=True)
    label = models.CharField(max_length=120)
    start_date = models.DateField()
    end_date = models.DateField()
    academic_year = models.CharField(max_length=16, db_index=True)
    synced_at = models.DateTimeField()
    class Meta:
        db_table = "leave_vacation_period"
        constraints = [models.CheckConstraint(condition=Q(end_date__gte=models.F("start_date")), name="leave_vacation_valid_date_range")]


class LeaveSLAConfiguration(models.Model):
    """Current reminder/escalation thresholds (hours) for actionable tasks."""
    role = models.CharField(max_length=64, unique=True)
    reminder_after_hours = models.PositiveIntegerField(default=24)
    escalate_after_hours = models.PositiveIntegerField(default=72)
    escalation_role = models.CharField(max_length=64, blank=True)
    escalation_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    updated_by_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = "leave_sla_configuration"


class LeaveRouteConfiguration(models.Model):
    """Current authority mapping by employee context and leave category."""
    category = models.ForeignKey(LeaveCategory, on_delete=models.CASCADE, related_name="routes")
    employee_kind = models.CharField(max_length=8, choices=EmployeeProfile.Kind.choices)
    designation = models.CharField(max_length=120, blank=True)
    unit_code = models.CharField(max_length=64, blank=True)
    final_authority_role = models.CharField(max_length=64)
    final_authority_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    establishment_role = models.CharField(max_length=64, blank=True)
    establishment_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    requires_substitute = models.BooleanField(default=False)
    active = models.BooleanField(default=True)
    updated_by_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = "leave_route_configuration"
        indexes = [models.Index(fields=["category", "employee_kind", "active"], name="leave_route_lookup_idx")]


class LeaveAuditEvent(models.Model):
    request = models.ForeignKey(LeaveRequest, on_delete=models.PROTECT, related_name="audit_events")
    action = models.CharField(max_length=48)
    from_status = models.CharField(max_length=32, blank=True)
    to_status = models.CharField(max_length=32, blank=True)
    actor_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    occurred_at = models.DateTimeField(auto_now_add=True)
    details = models.JSONField(default=dict, blank=True)
    class Meta:
        db_table = "leave_audit_event"
        ordering = ["occurred_at", "id"]


class LeaveNotificationOutbox(models.Model):
    """Transactional email delivery queue for assigned tasks and decisions."""
    class State(models.TextChoices):
        PENDING = "pending", "Pending"
        SENDING = "sending", "Sending"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    dedupe_key = models.CharField(max_length=160, unique=True)
    recipient_user_id = models.PositiveBigIntegerField(db_index=True)
    subject = models.CharField(max_length=200)
    body = models.TextField()
    payload = models.JSONField(default=dict, blank=True)
    state = models.CharField(max_length=12, choices=State.choices, default=State.PENDING, db_index=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.CharField(max_length=300, blank=True)
    claimed_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = "leave_notification_outbox"
        indexes = [models.Index(fields=["state", "created_at"], name="leave_notify_state_created_idx")]
