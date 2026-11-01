"""IAA-owned operational, configuration, evidence, and audit records.

Identity references are IAM user ids and intentionally have no user foreign key.
"""
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from modules.iaa.domain.state_machine import (
    ADMIN, AUDITOR, BASIC_USER, DEAN, DIRECTOR, FINANCE, HOD,
)
from modules.iaa.storage import PrivateEvidenceStorage

IAA_ROLES = [
    (BASIC_USER, BASIC_USER), (FINANCE, FINANCE), (HOD, HOD),
    (DEAN, DEAN), (DIRECTOR, DIRECTOR), (AUDITOR, AUDITOR), (ADMIN, ADMIN),
]


class FinancialYear(models.Model):
    code = models.CharField(max_length=32, unique=True)
    starts_on = models.DateField()
    ends_on = models.DateField()
    is_active = models.BooleanField(default=False)
    created_by_id = models.PositiveBigIntegerField()
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ("-starts_on", "code")
        constraints = [
            models.CheckConstraint(condition=models.Q(ends_on__gte=models.F("starts_on")),
                                   name="iaa_fy_dates_valid"),
        ]


class PolicyParameter(models.Model):
    """An administrator-configured policy value with an effective period."""
    code = models.CharField(max_length=80)
    value = models.JSONField()
    effective_from = models.DateField()
    effective_until = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    updated_by_id = models.PositiveBigIntegerField()
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ("code", "-effective_from")
        constraints = [
            models.UniqueConstraint(fields=("code", "effective_from"),
                                    name="iaa_policy_effective_unique"),
            models.CheckConstraint(
                condition=(models.Q(effective_until__isnull=True)
                           | models.Q(effective_until__gte=models.F("effective_from"))),
                name="iaa_policy_dates_valid"),
        ]


class DepartmentBudget(models.Model):
    financial_year = models.ForeignKey(FinancialYear, on_delete=models.PROTECT,
                                       related_name="budgets")
    department = models.CharField(max_length=120)
    available_amount = models.DecimalField(max_digits=14, decimal_places=2,
                                           validators=[MinValueValidator(0)])
    updated_by_id = models.PositiveBigIntegerField()
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ("department",)
        constraints = [
            models.UniqueConstraint(fields=("financial_year", "department"),
                                    name="iaa_budget_year_department_unique"),
            models.CheckConstraint(condition=models.Q(available_amount__gte=0),
                                   name="iaa_budget_nonnegative"),
        ]


class IaaRoleAssignment(models.Model):
    user_id = models.PositiveBigIntegerField(db_index=True)
    role = models.CharField(max_length=32, choices=IAA_ROLES)
    department = models.CharField(max_length=120, blank=True, default="")
    assigned_by_id = models.PositiveBigIntegerField()
    assigned_at = models.DateTimeField(default=timezone.now, editable=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("user_id", "role", "department")
        constraints = [
            models.UniqueConstraint(fields=("user_id", "role", "department"),
                                    name="iaa_role_user_scope_unique"),
            models.UniqueConstraint(
                fields=("role", "department"),
                condition=models.Q(is_active=True, role__in=(HOD, DEAN, DIRECTOR)),
                name="iaa_authority_scope_unique"),
        ]
        indexes = [models.Index(fields=("role", "department", "is_active"),
                                name="iaa_role_scope_idx")]


class ApprovalRouteRule(models.Model):
    request_type = models.CharField(max_length=80, blank=True, default="")
    department = models.CharField(max_length=120, blank=True, default="")
    minimum_amount = models.DecimalField(max_digits=14, decimal_places=2,
                                         null=True, blank=True)
    maximum_amount = models.DecimalField(max_digits=14, decimal_places=2,
                                         null=True, blank=True)
    levels = models.JSONField(default=list)
    escalation_roles = models.JSONField(default=list, blank=True)
    timeout_seconds = models.PositiveIntegerField(null=True, blank=True)
    priority = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    updated_by_id = models.PositiveBigIntegerField()
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ("-priority", "id")
        constraints = [
            models.CheckConstraint(
                condition=(models.Q(maximum_amount__isnull=True)
                           | models.Q(minimum_amount__isnull=True)
                           | models.Q(maximum_amount__gte=models.F("minimum_amount"))),
                name="iaa_route_amount_range_valid"),
        ]


class ExpenseVoucherRequest(models.Model):
    STATUS_CHOICES = [(x, x) for x in (
        "Draft", "Submitted", "Query Raised", "Query Responded",
        "Finance Validated", "Approval Pending", "Escalated", "Approved",
        "Rejected", "Recorded",
    )]
    created_by_id = models.PositiveBigIntegerField(db_index=True)
    department = models.CharField(max_length=120, blank=True, default="")
    request_type = models.CharField(max_length=80, blank=True, default="")
    amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True,
                                 validators=[MinValueValidator(0)])
    description = models.TextField(blank=True, default="")
    supporting_information = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default="Draft")
    assigned_finance_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    active_route_id = models.PositiveBigIntegerField(null=True, blank=True)
    current_approval_level = models.PositiveSmallIntegerField(default=0)
    submitted_at = models.DateTimeField(null=True, blank=True)
    recorded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ("-created_at", "-id")
        indexes = [
            models.Index(fields=("status", "-created_at"), name="iaa_req_status_idx"),
            models.Index(fields=("created_by_id", "-created_at"), name="iaa_req_owner_idx"),
            models.Index(fields=("department", "status"), name="iaa_req_dept_idx"),
        ]
        constraints = [
            models.CheckConstraint(condition=models.Q(amount__isnull=True) | models.Q(amount__gte=0),
                                   name="iaa_req_amount_nonnegative"),
            models.CheckConstraint(condition=models.Q(current_approval_level__gte=0),
                                   name="iaa_req_level_nonnegative"),
        ]


class TravelAllowanceClaim(models.Model):
    STATUS_CHOICES = [(x, x) for x in (
        "Submitted", "Query Raised", "Query Responded", "Verified",
        "Approval Pending", "Escalated", "Approved", "Rejected", "Recorded",
    )]
    claimant_user_id = models.PositiveBigIntegerField(db_index=True)
    department = models.CharField(max_length=120, blank=True, default="")
    trip_start = models.DateField(null=True, blank=True)
    trip_end = models.DateField(null=True, blank=True)
    purpose = models.TextField(blank=True, default="")
    claimed_amount = models.DecimalField(max_digits=14, decimal_places=2,
                                         null=True, blank=True,
                                         validators=[MinValueValidator(0)])
    trip_details = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default="Submitted")
    active_route_id = models.PositiveBigIntegerField(null=True, blank=True)
    current_approval_level = models.PositiveSmallIntegerField(default=0)
    submitted_at = models.DateTimeField(default=timezone.now, editable=False)
    recorded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ("-created_at", "-id")
        indexes = [
            models.Index(fields=("status", "-created_at"), name="iaa_ta_status_idx"),
            models.Index(fields=("claimant_user_id", "-created_at"), name="iaa_ta_owner_idx"),
            models.Index(fields=("department", "status"), name="iaa_ta_dept_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(models.Q(claimed_amount__isnull=True)
                           | models.Q(claimed_amount__gte=0)),
                name="iaa_ta_amount_nonnegative"),
            models.CheckConstraint(
                condition=(models.Q(trip_start__isnull=True)
                           | models.Q(trip_end__isnull=True)
                           | models.Q(trip_end__gte=models.F("trip_start"))),
                name="iaa_ta_trip_dates_valid"),
        ]


class Evidence(models.Model):
    record_type = models.CharField(max_length=32)
    record_id = models.PositiveBigIntegerField(db_index=True)
    purpose = models.CharField(max_length=80, blank=True, default="")
    file = models.FileField(upload_to="iaa/evidence/%Y/%m/%d",
                            storage=PrivateEvidenceStorage())
    original_filename = models.CharField(max_length=120)
    uploaded_by_id = models.PositiveBigIntegerField()
    uploaded_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ("uploaded_at", "id")
        indexes = [models.Index(fields=("record_type", "record_id"),
                                name="iaa_evidence_record_idx")]


class ApprovalStep(models.Model):
    STATUS_CHOICES = [(x, x) for x in ("Queued", "Pending", "Approved", "Rejected", "Escalated", "Superseded")]
    record_type = models.CharField(max_length=16)
    record_id = models.PositiveBigIntegerField(db_index=True)
    level = models.PositiveSmallIntegerField()
    authority_role = models.CharField(max_length=32, choices=IAA_ROLES)
    assigned_user_id = models.PositiveBigIntegerField(db_index=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="Pending")
    timeout_seconds = models.PositiveIntegerField(null=True, blank=True)
    escalation_roles = models.JSONField(default=list, blank=True)
    due_at = models.DateTimeField(null=True, blank=True)
    escalated_from_id = models.PositiveBigIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("level", "id")
        indexes = [
            models.Index(fields=("status", "due_at"), name="iaa_approval_due_idx"),
            models.Index(fields=("assigned_user_id", "status"), name="iaa_approval_user_idx"),
            models.Index(fields=("record_type", "record_id", "level"),
                         name="iaa_approval_record_idx"),
        ]
        constraints = [models.UniqueConstraint(
            fields=("record_type", "record_id", "level", "assigned_user_id", "escalated_from_id"),
            name="iaa_approval_assignment_unique")]


class ApprovalDecision(models.Model):
    step = models.ForeignKey(ApprovalStep, on_delete=models.PROTECT,
                             related_name="decisions")
    decision = models.CharField(max_length=16, choices=(("Approved", "Approved"), ("Rejected", "Rejected")))
    remarks = models.TextField()
    actor_user_id = models.PositiveBigIntegerField()
    actor_role = models.CharField(max_length=32, choices=IAA_ROLES)
    decided_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ("decided_at", "id")


class Anomaly(models.Model):
    STATUS_CHOICES = [(x, x) for x in ("Open", "Resolved", "Escalated")]
    record_type = models.CharField(max_length=16)
    record_id = models.PositiveBigIntegerField(db_index=True)
    category = models.CharField(max_length=80)
    description = models.TextField()
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="Open")
    resolver_role = models.CharField(max_length=32, choices=IAA_ROLES)
    assigned_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    created_by_id = models.PositiveBigIntegerField(null=True, blank=True)
    created_by_role = models.CharField(max_length=32, blank=True, default="System")
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at", "-id")
        indexes = [models.Index(fields=("status", "resolver_role"),
                                name="iaa_anomaly_queue_idx")]


class AuditObservation(models.Model):
    STATUS_CHOICES = [(x, x) for x in ("Open", "Responded", "Closed")]
    record_type = models.CharField(max_length=16)
    record_id = models.PositiveBigIntegerField(db_index=True)
    auditor_user_id = models.PositiveBigIntegerField()
    department = models.CharField(max_length=120, blank=True, default="")
    title = models.CharField(max_length=200)
    description = models.TextField()
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="Open")
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at", "-id")
        indexes = [models.Index(fields=("status", "department"),
                                name="iaa_observation_queue_idx")]


class AuditResponse(models.Model):
    observation = models.ForeignKey(AuditObservation, on_delete=models.PROTECT,
                                    related_name="responses")
    response = models.TextField()
    actor_user_id = models.PositiveBigIntegerField()
    actor_role = models.CharField(max_length=32, choices=IAA_ROLES)
    submitted_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ("submitted_at", "id")


class ActionHistory(models.Model):
    record_type = models.CharField(max_length=24)
    record_id = models.PositiveBigIntegerField(db_index=True)
    source_status = models.CharField(max_length=32, blank=True, default="")
    destination_status = models.CharField(max_length=32, blank=True, default="")
    action = models.CharField(max_length=64)
    actor_user_id = models.PositiveBigIntegerField(null=True, blank=True, db_index=True)
    actor_role = models.CharField(max_length=32, blank=True, default="System")
    remarks = models.TextField(blank=True, default="")
    details = models.JSONField(default=dict, blank=True)
    happened_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ("happened_at", "id")
        indexes = [models.Index(fields=("record_type", "record_id", "happened_at"),
                                name="iaa_history_record_idx")]


class IaaNotification(models.Model):
    user_id = models.PositiveBigIntegerField(db_index=True)
    actor_role = models.CharField(max_length=32, blank=True, default="")
    event = models.CharField(max_length=80)
    title = models.CharField(max_length=200)
    message = models.TextField()
    record_type = models.CharField(max_length=24, blank=True, default="")
    record_id = models.PositiveBigIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at", "-id")
        indexes = [models.Index(fields=("user_id", "read_at", "-created_at"),
                                name="iaa_notice_user_idx")]


class AutomaticAnomalyEvent(models.Model):
    CONDITION_CHOICES = (("budget_insufficient", "Budget insufficiency"),)
    record_type = models.CharField(max_length=16)
    record_id = models.PositiveBigIntegerField()
    condition = models.CharField(max_length=40, choices=CONDITION_CHOICES)
    context = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(
            fields=("record_type", "record_id", "condition"),
            name="iaa_auto_anomaly_event_unique")]
        indexes = [models.Index(fields=("processed_at", "created_at"),
                                name="iaa_auto_anomaly_pending_idx")]


class AutomaticAnomalyRule(models.Model):
    CONDITION_CHOICES = (("budget_insufficient", "Budget insufficiency"),)
    condition = models.CharField(max_length=40, choices=CONDITION_CHOICES, unique=True)
    category = models.CharField(max_length=80)
    description = models.TextField(blank=True, default="")
    resolver_role = models.CharField(max_length=32, choices=IAA_ROLES)
    assigned_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    updated_by_id = models.PositiveBigIntegerField()
    updated_at = models.DateTimeField(default=timezone.now)
