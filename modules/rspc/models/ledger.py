"""Append-only Financial Ledger model for RSPC.

In compliance with Step 2.7 of new-module-prompt.md:
Ledger rows are strictly append-only. No edits or deletions are permitted;
corrections are made via compensating reversing transactions.
"""

from __future__ import annotations

from django.core.exceptions import PermissionDenied
from django.db import models

from core.db.mixins import TimeStampedModel
from modules.rspc.models.budget import ProjectBudgetHead
from modules.rspc.models.project import Project


class ProjectFundTransaction(TimeStampedModel):
    """An immutable, append-only financial entry in a project's ledger."""

    TRANSACTION_TYPES = [
        ("allocation", "Fund Allocation / Sanction"),
        ("disbursement", "Disbursement / Expenditure"),
        ("reversal", "Reversal / Correction"),
    ]

    project = models.ForeignKey(Project, on_delete=models.PROTECT, related_name="transactions")
    budget_head = models.ForeignKey(
        ProjectBudgetHead, on_delete=models.PROTECT, related_name="transactions"
    )
    transaction_type = models.CharField(max_length=32, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    reference_no = models.CharField(max_length=128)
    description = models.TextField(blank=True)
    created_by_user_id = models.BigIntegerField()

    class Meta:
        db_table = "rspc_fund_transaction"
        indexes = [
            models.Index(fields=["project", "created_at"], name="rspc_tx_proj_idx"),
            models.Index(fields=["budget_head", "transaction_type"], name="rspc_tx_head_type_idx"),
        ]

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise PermissionDenied("Ledger entries are strictly immutable and cannot be updated.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionDenied("Ledger entries are strictly append-only and cannot be deleted.")

    def __str__(self) -> str:
        return (
            f"Tx#{self.pk} {self.transaction_type} {self.amount} "
            f"on {self.project.project_code} ({self.budget_head.head_type})"
        )
