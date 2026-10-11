"""Append-only leave ledger model.

Enforces ledger invariants for balances, credits, debits, lapses, and conversions.
"""
from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel
from modules.leave.domain.constants import LeaveCategory, LedgerTransactionType


class LeaveLedgerEntry(TimeStampedModel, UserScopedModel):
    category = models.CharField(max_length=10, choices=[(c.value, c.value) for c in LeaveCategory])
    delta_days = models.DecimalField(max_digits=5, decimal_places=1)
    transaction_type = models.CharField(
        max_length=20,
        choices=[(t.value, t.value) for t in LedgerTransactionType],
    )
    reason = models.CharField(max_length=255)
    reference_id = models.CharField(max_length=100, blank=True, db_index=True)
    created_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user_id", "category"]),
        ]
