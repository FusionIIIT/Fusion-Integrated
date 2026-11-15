"""IAA data. People are IAM user ids (plain integers), never foreign keys."""
from django.db import models

from core.db.mixins import TimeStampedModel
from modules.iaa import domain


class ExpenseRequest(TimeStampedModel):
    """An expense/voucher request moving through CW-IAA-01."""

    creator_user_id = models.IntegerField(db_index=True)
    department = models.CharField(max_length=100, blank=True)
    purpose = models.CharField(max_length=255, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=domain.STATUS_CHOICES,
                              default=domain.DRAFT, db_index=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    finance_user_id = models.IntegerField(null=True, blank=True)
    validated_at = models.DateTimeField(null=True, blank=True)
    approver_user_id = models.IntegerField(null=True, blank=True)
    decision_remarks = models.TextField(blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    recorded_by_user_id = models.IntegerField(null=True, blank=True)
    recorded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-id"]

    def __str__(self) -> str:
        return f"ExpenseRequest #{self.pk} ({self.status})"
