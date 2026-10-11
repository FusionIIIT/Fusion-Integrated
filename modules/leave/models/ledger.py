"""Append-only leave account (SRS-EL-053, SRS-EL-087)."""
from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel


class LeaveLedgerEntry(TimeStampedModel, UserScopedModel):
    TYPES = (("credit", "Credit"), ("debit", "Debit"), ("lapse", "Lapse"),
             ("conversion", "Conversion"), ("carry_forward", "Carry forward"),
             ("restoration", "Restoration"), ("reversal", "Reversal"),
             ("offline", "Offline"))

    category = models.CharField(max_length=4, db_index=True)
    year = models.PositiveIntegerField(db_index=True)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    entry_type = models.CharField(max_length=16, choices=TYPES)
    application = models.ForeignKey(
        "leave.LeaveApplication", null=True, blank=True,
        on_delete=models.PROTECT, related_name="ledger_entries")
    memo = models.CharField(max_length=300, blank=True)

    class Meta:
        db_table = "leave_ledger_entry"
        indexes = [
            models.Index(fields=["user_id", "category", "year"],
                         name="leave_ledger_balance"),
        ]
