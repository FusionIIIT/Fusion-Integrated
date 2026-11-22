from django.db import models

from core.db.mixins import TimeStampedModel


class AnomalyCategory(models.TextChoices):
    BUDGET_INSUFFICIENT = "budget_insufficient", "Department Budget Insufficient"
    POLICY_VIOLATION = "policy_violation", "Policy Violation"
    DUPLICATE_CLAIM = "duplicate_claim", "Duplicate Claim Suspected"
    MANUAL_FLAG = "manual_flag", "Manual Flag"


class AnomalyStatus(models.TextChoices):
    OPEN = "open", "Open"
    RESOLVED = "resolved", "Resolved"
    ESCALATED = "escalated", "Escalated"


class Anomaly(TimeStampedModel):
    category = models.CharField(max_length=64, choices=AnomalyCategory.choices)
    description = models.TextField()
    reference_type = models.CharField(max_length=32, db_index=True)
    reference_id = models.IntegerField(db_index=True)
    status = models.CharField(
        max_length=32,
        choices=AnomalyStatus.choices,
        default=AnomalyStatus.OPEN,
        db_index=True,
    )
    flagged_by_id = models.IntegerField(null=True, blank=True)
    flagged_by_role = models.CharField(max_length=64, default="system")
    resolver_role = models.CharField(max_length=64, default="finance_staff")
    resolved_by_id = models.IntegerField(null=True, blank=True)
    resolution_remarks = models.TextField(blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
