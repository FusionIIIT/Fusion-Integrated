"""ELM-owned persistence. All institute user references are plain integer ids."""

from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel, UserScopedModel


class LeavePolicy(TimeStampedModel):
    name = models.CharField(max_length=120)
    version = models.PositiveIntegerField()
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    published_by_user_id = models.IntegerField(null=True, blank=True)
    parameters = models.JSONField(default=dict)
    hierarchy = models.JSONField(default=dict)

    class Meta:
        db_table = "elm_leave_policy"
        constraints = [
            models.UniqueConstraint(fields=["name", "version"], name="elm_policy_name_version_uniq")
        ]
        indexes = [
            models.Index(fields=["effective_from", "effective_to"], name="elm_policy_effective_idx")
        ]

    @property
    def is_published(self):
        return self.published_at is not None


class CalendarVersion(TimeStampedModel):
    name = models.CharField(max_length=120)
    version = models.PositiveIntegerField()
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    published_by_user_id = models.IntegerField(null=True, blank=True)
    holidays = models.JSONField(default=list)
    restricted_holidays = models.JSONField(default=list)
    vacation_periods = models.JSONField(default=list)

    class Meta:
        db_table = "elm_calendar_version"
        constraints = [
            models.UniqueConstraint(
                fields=["name", "version"], name="elm_calendar_name_version_uniq"
            )
        ]
        indexes = [
            models.Index(
                fields=["effective_from", "effective_to"], name="elm_calendar_effective_idx"
            )
        ]


class LeaveRequest(TimeStampedModel, UserScopedModel):
    CATEGORY_CHOICES = [(x, x) for x in ("CL", "RH", "SCL", "EL", "COL", "VL")]
    KIND_CHOICES = [(x, x) for x in ("leave", "cancellation", "extension", "resumption", "offline")]
    STATUS_CHOICES = [
        (x, x)
        for x in (
            "draft",
            "awaiting_substitute",
            "unit_head_review",
            "establishment_review",
            "authority_review",
            "approved",
            "rejected",
            "withdrawn",
            "cancellation_pending",
            "cancelled",
            "extension_pending",
            "resumption_pending",
            "closed",
        )
    ]
    category = models.CharField(max_length=3, choices=CATEGORY_CHOICES)
    kind = models.CharField(max_length=16, choices=KIND_CHOICES, default="leave")
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default="draft", db_index=True)
    start_date = models.DateField()
    end_date = models.DateField()
    half_day = models.CharField(
        max_length=8,
        choices=[("none", "None"), ("first", "First half"), ("second", "Second half")],
        default="none",
    )
    chargeable_days = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    purpose = models.TextField()
    station_leave = models.BooleanField(default=False)
    station_leave_details = models.JSONField(default=dict, blank=True)
    substitute_user_id = models.IntegerField(null=True, blank=True)
    substitute_response = models.CharField(
        max_length=12,
        choices=[("pending", "Pending"), ("accepted", "Accepted"), ("declined", "Declined")],
        blank=True,
    )
    medical_evidence_ref = models.CharField(max_length=500, blank=True)
    policy_version_id = models.IntegerField(null=True, blank=True)
    calendar_version_id = models.IntegerField(null=True, blank=True)
    parent_request = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="related_requests"
    )
    unit_head_user_id = models.IntegerField(null=True, blank=True)
    current_approver_user_id = models.IntegerField(null=True, blank=True)
    decision_reason = models.TextField(blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    actual_resumption_date = models.DateField(null=True, blank=True)
    extra = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "elm_leave_request"
        indexes = [
            models.Index(fields=["user_id", "status"], name="elm_req_user_status_idx"),
            models.Index(fields=["start_date", "end_date"], name="elm_req_dates_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(end_date__gte=models.F("start_date")), name="elm_req_date_order"
            )
        ]


class WorkflowTask(TimeStampedModel):
    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE, related_name="tasks")
    task_type = models.CharField(max_length=32)
    assigned_user_id = models.IntegerField(null=True, blank=True)
    assigned_role = models.CharField(max_length=100, blank=True)
    status = models.CharField(
        max_length=16,
        choices=[
            ("open", "Open"),
            ("completed", "Completed"),
            ("cancelled", "Cancelled"),
            ("superseded", "Superseded"),
        ],
        default="open",
    )
    due_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    escalated_at = models.DateTimeField(null=True, blank=True)
    payload = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "elm_workflow_task"
        indexes = [
            models.Index(fields=["status", "due_at"], name="elm_task_due_idx"),
            models.Index(fields=["request", "status"], name="elm_task_req_status_idx"),
        ]


class LeaveLedgerEntry(TimeStampedModel):
    user_id = models.IntegerField(db_index=True)
    category = models.CharField(max_length=3, choices=LeaveRequest.CATEGORY_CHOICES)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    entry_type = models.CharField(
        max_length=24,
        choices=[
            ("credit", "Credit"),
            ("debit", "Debit"),
            ("restore", "Restore"),
            ("lapse", "Lapse"),
            ("conversion", "Conversion"),
            ("adjustment", "Adjustment"),
        ],
    )
    effective_date = models.DateField()
    request = models.ForeignKey(
        LeaveRequest, null=True, blank=True, on_delete=models.PROTECT, related_name="ledger_entries"
    )
    idempotency_key = models.CharField(max_length=180, unique=True)
    actor_user_id = models.IntegerField(null=True, blank=True)
    note = models.CharField(max_length=300, blank=True)

    class Meta:
        db_table = "elm_leave_ledger"
        indexes = [
            models.Index(
                fields=["user_id", "category", "effective_date"],
                name="elm_ledger_user_cat_date_idx",
            )
        ]


class AuditEvent(models.Model):
    request = models.ForeignKey(
        LeaveRequest,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="audit_events",
    )
    actor_user_id = models.IntegerField(null=True, blank=True)
    event_type = models.CharField(max_length=80)
    from_status = models.CharField(max_length=32, blank=True)
    to_status = models.CharField(max_length=32, blank=True)
    reason = models.TextField(blank=True)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "elm_audit_event"
        indexes = [
            models.Index(
                fields=["request", "created_at"],
                name="elm_audit_req_created_idx",
            )
        ]

    def __str__(self):
        return f"{self.event_type} #{self.pk or 'unsaved'}"

class YearEndRun(models.Model):
    year = models.PositiveSmallIntegerField()
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=16,
        choices=[("running", "Running"), ("completed", "Completed"), ("failed", "Failed")],
        default="running",
    )
    summary = models.JSONField(default=dict, blank=True)
    error = models.TextField(blank=True)

    class Meta:
        db_table = "elm_year_end_run"
        constraints = [models.UniqueConstraint(fields=["year"], name="elm_year_end_year_uniq")]
    def __str__(self):
        return f"{self.year} year-end run ({self.status})"
