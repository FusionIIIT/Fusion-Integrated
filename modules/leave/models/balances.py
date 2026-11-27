"""Balance ledger models for Employee Leave Management."""

from decimal import Decimal

from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel
from modules.leave.models.policy import LeaveType


class LeaveBalance(TimeStampedModel, UserScopedModel):
    """Current allocated and remaining balance per user per year."""

    leave_type = models.ForeignKey(LeaveType, on_delete=models.PROTECT, related_name="balances")
    year = models.PositiveIntegerField(db_index=True)
    credited_days = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal("0.0"))
    used_days = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal("0.0"))
    available_days = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal("0.0"))

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "leave_type", "year"],
                name="leave_balance_user_type_year_uniq",
            ),
            models.CheckConstraint(
                condition=models.Q(available_days__gte=0),
                name="leave_balance_available_days_nonneg",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"User {self.user_id} - {self.leave_type.code} "
            f"({self.year}): {self.available_days} avail"
        )


class LeaveLedgerEntry(TimeStampedModel):
    """Append-only audit trail of balance modifications (BR-EL-028, DEC-ELM-001)."""

    ENTRY_TYPES = [
        ("credit", "Credit"),
        ("debit", "Debit"),
        ("adjustment", "Adjustment"),
        ("lapse", "Lapse"),
        ("carry_forward", "Carry Forward"),
        ("conversion", "Conversion"),
    ]

    balance = models.ForeignKey(
        LeaveBalance, on_delete=models.CASCADE, related_name="ledger_entries"
    )
    entry_type = models.CharField(max_length=20, choices=ENTRY_TYPES)
    amount = models.DecimalField(max_digits=5, decimal_places=1)
    balance_after = models.DecimalField(max_digits=5, decimal_places=1)
    reference_type = models.CharField(
        max_length=30, blank=True
    )  # e.g., "leave_request", "resumption", "offline"
    reference_id = models.IntegerField(null=True, blank=True)
    description = models.CharField(max_length=255, blank=True)
    performed_by_user_id = models.IntegerField(null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.balance.user_id} - {self.entry_type} {self.amount} -> {self.balance_after}"
