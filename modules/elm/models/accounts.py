"""Leave balances and the ledger that explains them.

`LeaveAccount` holds the current balance per employee/category/year; every change
is written as a `LeaveTransaction`, so "why is my balance 6.5?" has an answer.
"""
from __future__ import annotations

from decimal import Decimal

from django.db import models

from core.db.mixins import TimeStampedModel


class LeaveAccount(TimeStampedModel):
    user_id = models.IntegerField(db_index=True)
    category = models.CharField(max_length=8)
    year = models.PositiveSmallIntegerField(db_index=True)
    balance = models.DecimalField(max_digits=7, decimal_places=2, default=Decimal("0"))
    used = models.DecimalField(max_digits=7, decimal_places=2, default=Decimal("0"))
    lapsed = models.DecimalField(max_digits=7, decimal_places=2, default=Decimal("0"))

    class Meta:
        db_table = "elm_leave_account"
        constraints = [
            models.UniqueConstraint(fields=["user_id", "category", "year"],
                                    name="elm_account_unique"),
        ]
        indexes = [
            models.Index(fields=["user_id", "year"], name="elm_account_user_idx"),
        ]
        ordering = ["category"]

    def __str__(self) -> str:
        return f"u{self.user_id} {self.category}/{self.year}={self.balance}"


class LeaveTransaction(TimeStampedModel):
    """Append-only ledger (BR-EL-036 record integrity)."""

    account = models.ForeignKey(LeaveAccount, on_delete=models.CASCADE,
                                related_name="transactions")
    kind = models.CharField(max_length=16)
    amount = models.DecimalField(max_digits=7, decimal_places=2)
    balance_after = models.DecimalField(max_digits=7, decimal_places=2)
    note = models.CharField(max_length=300, blank=True)
    request = models.ForeignKey("elm.LeaveRequest", null=True, blank=True,
                                on_delete=models.SET_NULL, related_name="ledger")
    actor_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "elm_leave_transaction"
        indexes = [
            models.Index(fields=["account", "-created_at"],
                         name="elm_ledger_account_idx"),
        ]
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"{self.kind} {self.amount} -> {self.balance_after}"
