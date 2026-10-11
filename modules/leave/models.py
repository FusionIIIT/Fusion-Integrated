"""Leave-owned persistence; IAM people remain integer references."""
from django.db import models
from django.db.models import Q

from modules.leave.domain.workflow import LEAVE_TYPES

LEAVE_TYPE_CHOICES = [(value, value) for value in LEAVE_TYPES]
REQUEST_KIND_CHOICES = [
    ("new", "New leave"), ("cancellation", "Cancellation"),
    ("extension", "Extension"),
]

STATUS_CHOICES = [(value, value.replace("_", " ").title()) for value in (
    "draft_not_submitted", "awaiting_substitute_response", "applicant_action_required",
    "awaiting_unit_head_review", "awaiting_establishment_routing",
    "awaiting_final_sanction_decision", "awaiting_director_self_sanction", "approved",
    "rejected", "withdrawn", "cancellation_pending_unit_head_review",
    "cancellation_pending_establishment", "cancellation_pending_final_decision",
    "cancelled", "cancellation_rejected_original_unchanged",
    "awaiting_extension_substitute_response", "extension_applicant_action_required",
    "awaiting_extension_unit_head_review", "extension_pending_establishment",
    "extension_pending_final_decision", "extended_incremental_period_posted",
    "extension_rejected_original_unchanged", "extension_request_withdrawn_original_unchanged",
)]


class LeavePolicy(models.Model):
    """Current configured parameters, without policy version lifecycle."""

    leave_type = models.CharField(max_length=3, choices=LEAVE_TYPE_CHOICES, unique=True)
    annual_entitlement = models.DecimalField(max_digits=7, decimal_places=2)
    applies_to = models.CharField(max_length=12, default="all")
    carry_forward = models.BooleanField(default=False)
    substitute_required = models.BooleanField(default=False)
    medical_evidence_required = models.BooleanField(default=False)
    higher_sanction = models.BooleanField(default=False)
    updated_by_user_id = models.BigIntegerField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["leave_type"], name="leave_policy_type_idx")]


class AuthorityRoute(models.Model):
    """ELM-owned current hierarchy configuration for an organizational unit."""

    unit_key = models.CharField(max_length=160)
    leave_type = models.CharField(max_length=3, choices=LEAVE_TYPE_CHOICES)
    unit_head_user_id = models.BigIntegerField()
    establishment_required = models.BooleanField(default=False)
    establishment_user_id = models.BigIntegerField(null=True, blank=True)
    final_authority_user_id = models.BigIntegerField(null=True, blank=True)
    updated_by_user_id = models.BigIntegerField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(
            fields=["unit_key", "leave_type"], name="leave_route_unit_type_uniq")]


class HolidayCalendar(models.Model):
    name = models.CharField(max_length=120)
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    is_published = models.BooleanField(default=False)
    is_current = models.BooleanField(default=False)
    created_by_user_id = models.BigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(
            fields=["is_current"], condition=Q(is_current=True),
            name="leave_one_current_calendar")]
        indexes = [models.Index(fields=["is_published", "effective_from"],
                                name="leave_calendar_effective_idx")]


class HolidayDate(models.Model):
    calendar = models.ForeignKey(HolidayCalendar, on_delete=models.CASCADE,
                                 related_name="dates")
    date = models.DateField()
    name = models.CharField(max_length=160)
    is_restricted_holiday = models.BooleanField(default=False)

    class Meta:
        constraints = [models.UniqueConstraint(
            fields=["calendar", "date"], name="leave_calendar_date_uniq")]


class LeaveApplication(models.Model):
    applicant_user_id = models.BigIntegerField(db_index=True)
    request_kind = models.CharField(max_length=16, choices=REQUEST_KIND_CHOICES,
                                    default="new")
    original_application = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT,
        related_name="related_requests")
    leave_type = models.CharField(max_length=3, choices=LEAVE_TYPE_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    requested_days = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    half_day_period = models.CharField(max_length=8, blank=True)
    purpose = models.TextField()
    station_leave = models.BooleanField(default=False)
    station_leave_details = models.CharField(max_length=500, blank=True)
    medical_evidence_reference = models.CharField(max_length=500, blank=True)
    organizational_unit = models.CharField(max_length=160, blank=True)
    status = models.CharField(max_length=64, choices=STATUS_CHOICES,
                              default="draft_not_submitted", db_index=True)
    substitute_required = models.BooleanField(default=False)
    substitute_user_id = models.BigIntegerField(null=True, blank=True)
    establishment_required = models.BooleanField(default=False)
    unit_head_user_id = models.BigIntegerField(null=True, blank=True)
    establishment_user_id = models.BigIntegerField(null=True, blank=True)
    final_authority_user_id = models.BigIntegerField(null=True, blank=True)
    recommendation = models.CharField(max_length=20, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    task_assigned_at = models.DateTimeField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["applicant_user_id", "-created_at"],
                         name="leave_app_owner_recent_idx"),
            models.Index(fields=["status", "-created_at"],
                         name="leave_app_status_recent_idx"),
            models.Index(fields=["substitute_user_id", "status"],
                         name="leave_app_sub_status_idx"),
            models.Index(fields=["unit_head_user_id", "status"],
                         name="leave_app_head_status_idx"),
            models.Index(fields=["final_authority_user_id", "status"],
                         name="leave_app_auth_status_idx"),
        ]
        constraints = [models.CheckConstraint(
            condition=Q(end_date__gte=models.F("start_date")),
            name="leave_app_dates_ordered")]


class LeaveDecision(models.Model):
    application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE,
                                    related_name="decisions")
    event = models.CharField(max_length=40)
    from_status = models.CharField(max_length=64)
    to_status = models.CharField(max_length=64)
    actor_user_id = models.BigIntegerField(null=True, blank=True)
    actor_kind = models.CharField(max_length=48)
    outcome = models.CharField(max_length=32, blank=True)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "pk"]
        indexes = [models.Index(fields=["application", "created_at"],
                                name="leave_decision_history_idx")]


class SubstituteResponse(models.Model):
    application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE,
                                    related_name="substitute_responses")
    substitute_user_id = models.BigIntegerField()
    response = models.CharField(max_length=8, choices=[("accept", "Accept"), ("decline", "Decline")])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "pk"]


class LeaveAccountTransaction(models.Model):
    user_id = models.BigIntegerField(db_index=True)
    leave_type = models.CharField(max_length=3, choices=LEAVE_TYPE_CHOICES)
    year = models.PositiveSmallIntegerField()
    amount = models.DecimalField(max_digits=9, decimal_places=2)
    transaction_type = models.CharField(max_length=32)
    application = models.ForeignKey(LeaveApplication, null=True, blank=True,
                                    on_delete=models.PROTECT)
    source_key = models.CharField(max_length=180, unique=True)
    note = models.CharField(max_length=300, blank=True)
    created_by_user_id = models.BigIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["user_id", "leave_type", "year"],
                                name="leave_ledger_account_idx")]


class ResumptionRecord(models.Model):
    application = models.ForeignKey(LeaveApplication, on_delete=models.PROTECT,
                                    related_name="resumptions")
    employee_user_id = models.BigIntegerField(db_index=True)
    actual_resumption_date = models.DateField()
    state = models.CharField(max_length=40, default="resumption_review_pending")
    reviewed_by_user_id = models.BigIntegerField(null=True, blank=True)
    synchronization_status = models.CharField(max_length=32, default="not_required")
    synchronization_error = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(
            fields=["application"], name="leave_resumption_once")]


class SlaConfiguration(models.Model):
    task_kind = models.CharField(max_length=48, unique=True)
    reminder_after_hours = models.PositiveIntegerField(null=True, blank=True)
    escalation_after_hours = models.PositiveIntegerField(null=True, blank=True)
    escalation_user_id = models.BigIntegerField(null=True, blank=True)
    updated_by_user_id = models.BigIntegerField()
    updated_at = models.DateTimeField(auto_now=True)


class LeaveNotification(models.Model):
    topic = models.CharField(max_length=48)
    dedupe_key = models.CharField(max_length=180, unique=True)
    recipient_user_id = models.BigIntegerField()
    subject = models.CharField(max_length=180)
    body = models.TextField()
    status = models.CharField(max_length=16, default="pending")
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.CharField(max_length=300, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class LeaveRecordCorrection(models.Model):
    application = models.ForeignKey(LeaveApplication, null=True, blank=True,
                                    on_delete=models.PROTECT)
    user_id = models.BigIntegerField()
    leave_type = models.CharField(max_length=3, choices=LEAVE_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=9, decimal_places=2)
    reason = models.CharField(max_length=300)
    actor_user_id = models.BigIntegerField()
    transaction = models.OneToOneField(LeaveAccountTransaction, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
