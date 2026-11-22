"""IAA-owned data. Institute identities are integer references from Fusion IAM."""

from django.db import models
from django.db.models import Q


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.__class__.__name__} #{self.pk or 'unsaved'}"


class IaaPolicy(TimestampedModel):
    """Configuration values are institution-controlled, never code constants."""

    name = models.CharField(max_length=100, unique=True)
    financial_year_start_month = models.PositiveSmallIntegerField(default=4)
    ta_high_value_threshold = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    approval_timeout_hours = models.PositiveIntegerField(null=True, blank=True)
    parameters = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    configured_by_user_id = models.PositiveBigIntegerField(null=True, blank=True)

    class Meta:
        db_table = "iaa_policy"

    def __str__(self):
        return self.name


class ApprovalRoute(TimestampedModel):
    """A routing band and one authority level in the configured hierarchy."""

    request_type = models.CharField(max_length=40)
    department = models.CharField(max_length=120, blank=True)
    amount_from = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    amount_through = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    level = models.PositiveSmallIntegerField()
    authority_role = models.CharField(
        max_length=20, choices=[("hod", "HoD"), ("dean", "Dean"), ("director", "Director")]
    )
    assignee_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    timeout_hours = models.PositiveIntegerField(null=True, blank=True)
    next_route = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="prior_routes"
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "iaa_approval_route"
        ordering = ("level", "id")
        indexes = [
            models.Index(
                fields=("request_type", "department", "is_active"), name="iaa_route_match_idx"
            )
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(amount_through__isnull=True)
                | Q(amount_through__gte=models.F("amount_from")),
                name="iaa_route_amount_range",
            )
        ]

    def __str__(self):
        return f"{self.request_type} {self.department or '*'} level {self.level}"


class BudgetAllocation(TimestampedModel):
    department = models.CharField(max_length=120)
    financial_year = models.CharField(max_length=16)
    budget_code = models.CharField(max_length=60)
    allocated_amount = models.DecimalField(max_digits=14, decimal_places=2)
    committed_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    available_amount = models.DecimalField(max_digits=14, decimal_places=2)
    configured_by_user_id = models.PositiveBigIntegerField(null=True, blank=True)

    class Meta:
        db_table = "iaa_budget_allocation"
        constraints = [
            models.UniqueConstraint(
                fields=("department", "financial_year", "budget_code"), name="iaa_budget_unique"
            )
        ]

    def __str__(self):
        return f"{self.department} {self.financial_year} {self.budget_code}"


class IaaSupportingDocument(TimestampedModel):
    """A validated Drive link owned by the employee who attached it."""

    KINDS = [
        ("expense", "Expense/voucher"),
        ("ta", "Travel claim"),
        ("observation", "Corrective evidence"),
    ]
    user_id = models.PositiveBigIntegerField(db_index=True)
    kind = models.CharField(max_length=16, choices=KINDS)
    title = models.CharField(max_length=160)
    drive_url = models.URLField(max_length=500)
    drive_file_id = models.CharField(max_length=200)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "iaa_supporting_document"
        constraints = [
            models.UniqueConstraint(
                fields=("user_id", "drive_file_id", "kind"), name="iaa_doc_user_file_kind_uniq"
            )
        ]

    def __str__(self):
        return self.title


class ExpenseRequest(TimestampedModel):
    STATUS = [
        (s, s.replace("_", " ").title())
        for s in (
            "draft",
            "submitted",
            "query_raised",
            "query_responded",
            "finance_validated",
            "approval_pending",
            "approved",
            "rejected",
            "recorded",
        )
    ]

    creator_user_id = models.PositiveBigIntegerField(db_index=True)
    request_type = models.CharField(max_length=40)
    amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    department = models.CharField(max_length=120, blank=True)
    description = models.TextField(blank=True)
    supporting_documents = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=24, choices=STATUS, default="draft", db_index=True)
    assigned_finance_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    assigned_route = models.ForeignKey(
        ApprovalRoute,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="expense_requests",
    )
    clarification = models.TextField(blank=True)
    finance_notes = models.TextField(blank=True)
    decision_remarks = models.TextField(blank=True)
    recorded_at = models.DateTimeField(null=True, blank=True)
    recorded_by_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    lock_version = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "iaa_expense_request"
        indexes = [
            models.Index(fields=("creator_user_id", "status"), name="iaa_exp_user_status_idx"),
            models.Index(fields=("department", "status"), name="iaa_exp_dept_status_idx"),
        ]

    def __str__(self):
        return f"Expense request #{self.pk or 'unsaved'}"


class TravelClaim(TimestampedModel):
    STATUS = [
        (s, s.replace("_", " ").title())
        for s in (
            "submitted",
            "query_raised",
            "query_responded",
            "verified",
            "approval_pending",
            "approved",
            "rejected",
            "recorded",
        )
    ]

    claimant_user_id = models.PositiveBigIntegerField(db_index=True)
    department = models.CharField(max_length=120)
    trip_start = models.DateField()
    trip_end = models.DateField()
    purpose = models.TextField()
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    supporting_documents = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=24, choices=STATUS, default="submitted", db_index=True)
    assigned_finance_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    assigned_route = models.ForeignKey(
        ApprovalRoute, null=True, blank=True, on_delete=models.PROTECT, related_name="travel_claims"
    )
    clarification = models.TextField(blank=True)
    finance_notes = models.TextField(blank=True)
    decision_remarks = models.TextField(blank=True)
    recorded_at = models.DateTimeField(null=True, blank=True)
    recorded_by_user_id = models.PositiveBigIntegerField(null=True, blank=True)

    class Meta:
        db_table = "iaa_travel_claim"
        indexes = [
            models.Index(fields=("claimant_user_id", "status"), name="iaa_ta_user_status_idx")
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(trip_end__gte=models.F("trip_start")), name="iaa_ta_date_range"
            )
        ]

    def __str__(self):
        return f"Travel claim #{self.pk or 'unsaved'}"


class ApprovalStep(TimestampedModel):
    RECORD_TYPES = [("expense", "Expense/voucher"), ("ta", "Travel claim")]
    STATUS = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("escalated", "Escalated"),
        ("superseded", "Superseded"),
    ]

    record_type = models.CharField(max_length=12, choices=RECORD_TYPES)
    record_id = models.PositiveBigIntegerField(db_index=True)
    route = models.ForeignKey(ApprovalRoute, on_delete=models.PROTECT, related_name="steps")
    level = models.PositiveSmallIntegerField()
    authority_role = models.CharField(max_length=20)
    assignee_user_id = models.PositiveBigIntegerField(db_index=True)
    status = models.CharField(max_length=12, choices=STATUS, default="pending")
    due_at = models.DateTimeField(null=True, blank=True, db_index=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    remarks = models.TextField(blank=True)

    class Meta:
        db_table = "iaa_approval_step"
        ordering = ("level", "id")
        indexes = [
            models.Index(fields=("assignee_user_id", "status"), name="iaa_step_assignee_idx")
        ]

    def __str__(self):
        return f"{self.authority_role} approval for {self.record_type} #{self.record_id}"


class Anomaly(TimestampedModel):
    STATUS = [("open", "Open"), ("resolved", "Resolved"), ("escalated", "Escalated")]
    RECORD_TYPES = [("expense", "Expense/voucher"), ("ta", "Travel claim")]

    record_type = models.CharField(max_length=12, choices=RECORD_TYPES)
    record_id = models.PositiveBigIntegerField(db_index=True)
    category = models.CharField(max_length=80)
    description = models.TextField()
    is_automatic = models.BooleanField(default=False)
    status = models.CharField(max_length=12, choices=STATUS, default="open", db_index=True)
    resolver_role = models.CharField(max_length=20)
    resolver_user_id = models.PositiveBigIntegerField(null=True, blank=True, db_index=True)
    resolution_remarks = models.TextField(blank=True)

    class Meta:
        db_table = "iaa_anomaly"
        constraints = [
            models.UniqueConstraint(
                fields=("record_type", "record_id", "category"),
                condition=Q(status="open"),
                name="iaa_anom_open_uniq",
            )
        ]

    def __str__(self):
        return f"{self.category} anomaly for {self.record_type} #{self.record_id}"


class AuditObservation(TimestampedModel):
    STATUS = [("open", "Open"), ("responded", "Responded"), ("closed", "Closed")]
    RECORD_TYPES = [("expense", "Expense/voucher"), ("ta", "Travel claim")]

    record_type = models.CharField(max_length=12, choices=RECORD_TYPES)
    record_id = models.PositiveBigIntegerField(db_index=True)
    auditor_user_id = models.PositiveBigIntegerField(db_index=True)
    owner_user_id = models.PositiveBigIntegerField(db_index=True)
    department = models.CharField(max_length=120)
    finding = models.TextField()
    status = models.CharField(max_length=12, choices=STATUS, default="open", db_index=True)

    class Meta:
        db_table = "iaa_audit_observation"

    def __str__(self):
        return f"Audit observation #{self.pk or 'unsaved'}"


class ObservationResponse(TimestampedModel):
    observation = models.ForeignKey(
        AuditObservation, on_delete=models.PROTECT, related_name="responses"
    )
    responder_user_id = models.PositiveBigIntegerField()
    corrective_action = models.TextField()
    supporting_documents = models.JSONField(default=list, blank=True)
    auditor_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    satisfactory = models.BooleanField(null=True, blank=True)
    verification_remarks = models.TextField(blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "iaa_observation_response"
        ordering = ("created_at", "id")

    def __str__(self):
        return f"Observation response #{self.pk or 'unsaved'}"


class IaaAuditEvent(models.Model):
    record_type = models.CharField(max_length=24)
    record_id = models.PositiveBigIntegerField(db_index=True)
    actor_user_id = models.PositiveBigIntegerField(null=True, blank=True, db_index=True)
    active_role = models.CharField(max_length=20, blank=True)
    action = models.CharField(max_length=80)
    from_status = models.CharField(max_length=24, blank=True)
    to_status = models.CharField(max_length=24, blank=True)
    details = models.JSONField(default=dict, blank=True)
    occurred_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "iaa_audit_event"
        ordering = ("occurred_at", "id")

    def __str__(self):
        return f"{self.action} event #{self.pk or 'unsaved'}"


class IaaNotificationOutbox(models.Model):
    recipient_user_id = models.PositiveBigIntegerField(db_index=True)
    record_type = models.CharField(max_length=24)
    record_id = models.PositiveBigIntegerField()
    event = models.CharField(max_length=80)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "iaa_notification_outbox"
        indexes = [
            models.Index(fields=("delivered_at", "created_at"), name="iaa_outbox_pending_idx")
        ]

    def __str__(self):
        return f"{self.event} notification #{self.pk or 'unsaved'}"


class IaaProcessingIssue(models.Model):
    """Recoverable issue that blocks a false success state."""

    STATUS = [("open", "Open"), ("resolved", "Resolved")]
    record_type = models.CharField(
        max_length=12, choices=[("expense", "Expense/voucher"), ("ta", "Travel claim")]
    )
    record_id = models.PositiveBigIntegerField(db_index=True)
    operation = models.CharField(max_length=60)
    reason = models.CharField(max_length=300)
    status = models.CharField(max_length=12, choices=STATUS, default="open", db_index=True)
    reported_by_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    resolved_by_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "iaa_processing_issue"
        indexes = [models.Index(fields=("status", "created_at"), name="iaa_issue_status_idx")]

    def __str__(self):
        return f"{self.operation} issue #{self.pk or 'unsaved'}"
