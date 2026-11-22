from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel, UserScopedModel
from modules.iaa.domain import state_machine as sm

STATUS_CHOICES = [(s, s.replace("_", " ").title()) for s in sm.RECORD_STATES]


class FinancialRecord(TimeStampedModel, UserScopedModel):
    """An expense/voucher request or a TA claim; `user_id` is its creator or claimant."""

    KIND_CHOICES = [(sm.EXPENSE, "Expense / voucher"), (sm.TA, "Travel allowance")]

    kind = models.CharField(max_length=8, choices=KIND_CHOICES)
    status = models.CharField(max_length=24, choices=STATUS_CHOICES)
    department = models.CharField(max_length=128, blank=True)
    request_type = models.CharField(max_length=64, blank=True)
    title = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    purpose = models.TextField(blank=True)
    trip_start = models.DateField(null=True, blank=True)
    trip_end = models.DateField(null=True, blank=True)
    financial_year = models.ForeignKey("iaa.FinancialYear", null=True, blank=True,
                                       on_delete=models.PROTECT, related_name="records")
    submitted_at = models.DateTimeField(null=True, blank=True)
    # Snapshot of the route at hand-off, so a later policy never moves an item in flight.
    route_levels = models.JSONField(default=list, blank=True)
    escalation_designation = models.CharField(max_length=64, blank=True)
    current_level = models.PositiveSmallIntegerField(null=True, blank=True)
    processing_reference = models.CharField(max_length=128, blank=True)
    processing_note = models.TextField(blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    processed_by = models.IntegerField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(amount__isnull=True) | Q(amount__gt=0),
                                   name="iaa_record_amount_positive"),
            models.CheckConstraint(
                condition=~Q(kind=sm.TA) | Q(trip_start__isnull=False, trip_end__isnull=False),
                name="iaa_record_ta_has_trip_dates"),
            models.CheckConstraint(
                condition=Q(trip_start__isnull=True) | Q(trip_end__isnull=True)
                | Q(trip_end__gte=models.F("trip_start")),
                name="iaa_record_trip_ordered"),
            models.CheckConstraint(condition=Q(status__in=sm.RECORD_STATES),
                                   name="iaa_record_status_known"),
        ]
        indexes = [
            models.Index(fields=["user_id", "-created_at"], name="iaa_record_owner_idx"),
            models.Index(fields=["status", "-created_at"], name="iaa_record_status_idx"),
            models.Index(fields=["department", "status"], name="iaa_record_dept_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.kind}#{self.pk}"


class SupportingDocument(TimeStampedModel):
    record = models.ForeignKey(FinancialRecord, on_delete=models.PROTECT,
                               related_name="documents")
    title = models.CharField(max_length=200)
    link = models.URLField(max_length=500)
    added_by = models.IntegerField()

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["record", "created_at"], name="iaa_doc_record_idx")]


class ClarificationQuery(TimeStampedModel):
    record = models.ForeignKey(FinancialRecord, on_delete=models.PROTECT, related_name="queries")
    question = models.TextField()
    raised_by = models.IntegerField()
    raised_role = models.CharField(max_length=64)
    response = models.TextField(blank=True)
    responded_by = models.IntegerField(null=True, blank=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(fields=["record"], condition=Q(responded_at__isnull=True),
                                    name="iaa_query_one_open_per_record"),
        ]
        indexes = [models.Index(fields=["record", "created_at"], name="iaa_query_record_idx")]


class ApprovalStep(TimeStampedModel):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"
    REROUTED = "rerouted"
    STATUSES = [(s, s.title()) for s in (PENDING, APPROVED, REJECTED, ESCALATED, REROUTED)]

    record = models.ForeignKey(FinancialRecord, on_delete=models.PROTECT, related_name="steps")
    level = models.PositiveSmallIntegerField()
    designation = models.CharField(max_length=64)
    status = models.CharField(max_length=12, choices=STATUSES, default=PENDING)
    assigned_at = models.DateTimeField()
    via_escalation = models.BooleanField(default=False)
    decided_by = models.IntegerField(null=True, blank=True)
    decided_role = models.CharField(max_length=64, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    remarks = models.TextField(blank=True)

    class Meta:
        ordering = ["assigned_at", "id"]
        constraints = [
            models.UniqueConstraint(fields=["record"], condition=Q(status="pending"),
                                    name="iaa_step_one_pending_per_record"),
            models.CheckConstraint(
                condition=~Q(status__in=["approved", "rejected"]) | ~Q(remarks=""),
                name="iaa_step_decision_has_remarks"),
        ]
        indexes = [
            models.Index(fields=["designation", "status"], name="iaa_step_queue_idx"),
            models.Index(fields=["status", "assigned_at"], name="iaa_step_overdue_idx"),
        ]
