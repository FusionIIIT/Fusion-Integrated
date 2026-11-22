from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel
from modules.iaa.models._append_only import AppendOnlyModel


class FinancialYear(TimeStampedModel):
    code = models.CharField(max_length=16, unique=True)
    starts_on = models.DateField()
    ends_on = models.DateField()

    class Meta:
        ordering = ["-starts_on"]
        constraints = [
            models.CheckConstraint(condition=Q(ends_on__gt=models.F("starts_on")),
                                   name="iaa_fy_ends_after_start"),
        ]
        indexes = [models.Index(fields=["starts_on", "ends_on"], name="iaa_fy_span_idx")]

    def __str__(self) -> str:
        return self.code


class PolicyVersion(AppendOnlyModel):
    """Effective-dated and never edited: a change is a newer version (Step 2.8)."""

    effective_from = models.DateTimeField()
    approval_timeout_hours = models.PositiveIntegerField()
    ta_high_value_threshold = models.DecimalField(max_digits=14, decimal_places=2)
    budget_check_required = models.BooleanField(default=True)
    request_types = models.JSONField(default=list)
    required_documents = models.JSONField(default=dict)
    routes = models.JSONField(default=list)
    anomaly_resolvers = models.JSONField(default=dict)
    created_by = models.IntegerField()
    created_role = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-effective_from", "-id"]
        constraints = [
            models.CheckConstraint(condition=Q(approval_timeout_hours__gt=0),
                                   name="iaa_policy_timeout_positive"),
            models.CheckConstraint(condition=Q(ta_high_value_threshold__gte=0),
                                   name="iaa_policy_threshold_nonneg"),
        ]
        indexes = [models.Index(fields=["-effective_from"], name="iaa_policy_effective_idx")]


class BudgetEntry(AppendOnlyModel):
    """The departmental budget ledger; a correction is a reversing row (Step 2.7)."""

    ALLOCATION = "allocation"
    ADJUSTMENT = "adjustment"
    COMMITMENT = "commitment"
    KINDS = [(ALLOCATION, "Allocation"), (ADJUSTMENT, "Adjustment"), (COMMITMENT, "Commitment")]

    financial_year = models.ForeignKey(FinancialYear, on_delete=models.PROTECT,
                                       related_name="budget_entries")
    department = models.CharField(max_length=128)
    kind = models.CharField(max_length=16, choices=KINDS)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    record = models.ForeignKey("iaa.FinancialRecord", null=True, blank=True,
                               on_delete=models.PROTECT, related_name="budget_entries")
    note = models.CharField(max_length=255, blank=True)
    created_by = models.IntegerField(null=True)
    created_role = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=~Q(kind="commitment") | Q(amount__lt=0),
                                   name="iaa_budget_commitment_negative"),
            models.CheckConstraint(condition=~Q(kind="allocation") | Q(amount__gt=0),
                                   name="iaa_budget_allocation_positive"),
            models.UniqueConstraint(fields=["record"], condition=Q(kind="commitment"),
                                    name="iaa_budget_one_commitment_per_record"),
        ]
        indexes = [models.Index(fields=["financial_year", "department"],
                                name="iaa_budget_dept_idx")]
