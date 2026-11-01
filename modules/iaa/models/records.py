from django.db import models
from django.utils import timezone


class Timestamped(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        abstract = True


class IAAExpenseRequest(Timestamped):
    KIND = [("expense", "Expense"), ("voucher", "Voucher")]
    STATUS = [(x, x.replace("_", " ").title()) for x in (
        "draft", "submitted", "finance_review", "clarification",
        "pending_approval", "approved", "rejected", "processed", "cancelled")]
    claimant_user_id = models.PositiveBigIntegerField(db_index=True)
    department_id = models.CharField(max_length=80, blank=True)
    request_type = models.CharField(max_length=16, choices=KIND)
    title = models.CharField(max_length=180)
    description = models.TextField(blank=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=3, default="INR")
    financial_year = models.CharField(max_length=9)
    budget_code = models.CharField(max_length=80, blank=True)
    attachments = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=24, choices=STATUS, default="draft", db_index=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    locked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "iaa_expense_request"
        ordering = ["-created_at"]

    @property
    def is_locked(self):
        return self.locked_at is not None


class IAAApproval(Timestamped):
    DECISIONS = [("approved", "Approved"), ("rejected", "Rejected"),
                 ("escalated", "Escalated")]
    request = models.ForeignKey(IAAExpenseRequest, on_delete=models.CASCADE,
                                related_name="approvals")
    level = models.PositiveSmallIntegerField(default=1)
    approver_user_id = models.PositiveBigIntegerField(db_index=True)
    approver_role = models.CharField(max_length=80)
    decision = models.CharField(max_length=16, choices=DECISIONS)
    remarks = models.TextField()
    decided_at = models.DateTimeField(default=timezone.now)
    class Meta:
        db_table = "iaa_approval"
        ordering = ["level", "decided_at"]
        constraints = [models.UniqueConstraint(fields=["request", "level"],
                                                name="iaa_one_decision_per_level")]


class IAAAnomaly(Timestamped):
    STATUS = [("open", "Open"), ("investigating", "Investigating"),
              ("resolved", "Resolved"), ("escalated", "Escalated")]
    request = models.ForeignKey(IAAExpenseRequest, null=True, blank=True,
                                on_delete=models.SET_NULL, related_name="anomalies")
    reference = models.CharField(max_length=100, blank=True)
    category = models.CharField(max_length=80)
    description = models.TextField()
    status = models.CharField(max_length=16, choices=STATUS, default="open")
    raised_by_user_id = models.PositiveBigIntegerField()
    resolution = models.TextField(blank=True)
    resolved_by_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    class Meta:
        db_table = "iaa_anomaly"
        ordering = ["-created_at"]


class IAAAuditObservation(Timestamped):
    STATUS = [("open", "Open"), ("responded", "Responded"),
              ("closed", "Closed")]
    reference = models.CharField(max_length=100, unique=True)
    title = models.CharField(max_length=180)
    finding = models.TextField()
    owner_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    response = models.TextField(blank=True)
    closure_evidence = models.TextField(blank=True)
    status = models.CharField(max_length=24, choices=STATUS, default="open")
    raised_by_user_id = models.PositiveBigIntegerField()
    class Meta:
        db_table = "iaa_audit_observation"
        ordering = ["-created_at"]


class IATravelClaim(Timestamped):
    STATUS = [(x, x.replace("_", " ").title()) for x in (
        "draft", "submitted", "verified", "pending_approval", "approved",
        "rejected", "processed")]
    claimant_user_id = models.PositiveBigIntegerField(db_index=True)
    trip_purpose = models.CharField(max_length=180)
    start_date = models.DateField()
    end_date = models.DateField()
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=3, default="INR")
    details = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=24, choices=STATUS, default="draft", db_index=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    class Meta:
        db_table = "iaa_travel_claim"
        ordering = ["-created_at"]


class IAAPolicy(Timestamped):
    """Configurable policy: no monetary approval threshold is hard-coded."""
    financial_year = models.CharField(max_length=9, unique=True)
    parameters = models.JSONField(default=dict, blank=True)
    approval_rules = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=False)
    updated_by_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    class Meta:
        db_table = "iaa_policy"


class IAAAuditEvent(models.Model):
    aggregate_type = models.CharField(max_length=40)
    aggregate_id = models.PositiveBigIntegerField()
    action = models.CharField(max_length=80)
    actor_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    actor_role = models.CharField(max_length=80, blank=True)
    before = models.JSONField(default=dict, blank=True)
    after = models.JSONField(default=dict, blank=True)
    remarks = models.TextField(blank=True)
    occurred_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        db_table = "iaa_audit_event"
        ordering = ["-occurred_at"]
        indexes = [models.Index(fields=["aggregate_type", "aggregate_id"],
                                name="iaa_audit_aggregate_idx")]
