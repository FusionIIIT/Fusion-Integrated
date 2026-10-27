"""Leave balances and ledger tracking."""
from __future__ import annotations

from decimal import Decimal
from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel


class LeaveBalance(TimeStampedModel, UserScopedModel):
    """Annual entitlement and running balance for an employee."""

    year = models.PositiveSmallIntegerField(db_index=True)
    is_faculty = models.BooleanField(default=False)
    year_end_processed = models.BooleanField(default=False)

    cl_balance = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal("8.0"))
    rh_balance = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal("2.0"))
    scl_balance = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal("15.0"))
    el_balance = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("30.00"))
    vl_balance = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal("60.0"))
    col_balance = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal("20.0"))

    class Meta:
        db_table = "leave_balance"
        constraints = [
            models.UniqueConstraint(fields=["user_id", "year"], name="leave_balance_unique_user_year"),
        ]
        indexes = [
            models.Index(fields=["user_id", "year"], name="leave_balance_user_year_idx"),
        ]

    def __str__(self) -> str:
        return f"user={self.user_id} year={self.year}"

    def get_category_balance(self, category: str) -> Decimal:
        field_name = f"{category.lower()}_balance"
        return getattr(self, field_name, Decimal("0.0"))

    def deduct(self, category: str, days: Decimal) -> None:
        field_name = f"{category.lower()}_balance"
        current = getattr(self, field_name)
        setattr(self, field_name, current - days)

    def credit(self, category: str, days: Decimal) -> None:
        field_name = f"{category.lower()}_balance"
        current = getattr(self, field_name)
        setattr(self, field_name, current + days)


class LeaveLedgerEntry(TimeStampedModel, UserScopedModel):
    """Immutable audit trail of credit/debit adjustments."""

    TYPES = [
        ("credit", "Annual Credit"),
        ("debit", "Leave Availment"),
        ("reversal", "Cancellation Reversal"),
        ("conversion", "VL to EL Conversion"),
        ("carry_forward", "Year-End Carry-Forward"),
        ("lapse", "Year-End Lapse"),
        ("adjustment", "Resumption Adjustment"),
    ]

    balance = models.ForeignKey(LeaveBalance, on_delete=models.CASCADE, related_name="ledger_entries")
    category = models.CharField(max_length=10)
    entry_type = models.CharField(max_length=20, choices=TYPES)
    change_amount = models.DecimalField(max_digits=6, decimal_places=2)
    balance_after = models.DecimalField(max_digits=6, decimal_places=2)
    reference_id = models.IntegerField(null=True, blank=True)
    remarks = models.TextField(blank=True)

    class Meta:
        db_table = "leave_ledger_entry"
        ordering = ["-created_at"]
