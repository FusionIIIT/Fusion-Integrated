"""Append-only leave ledger for balance tracking."""

from django.db import models


class LedgerEntry(models.Model):
    user_id = models.IntegerField(db_index=True)
    year = models.IntegerField(db_index=True)
    category = models.CharField(max_length=8, db_index=True)
    days = models.DecimalField(max_digits=5, decimal_places=2)
    reason = models.CharField(max_length=64)
    request_id = models.IntegerField(null=True, blank=True, db_index=True)
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "leave_ledger_entry"
        indexes = [
            models.Index(fields=["user_id", "year", "category"], name="leave_ledger_user_yr_idx"),
        ]

    def __str__(self) -> str:
        return f"Ledger#{self.pk} u{self.user_id} {self.category} {self.days} ({self.reason})"
