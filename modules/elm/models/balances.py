"""Leave balances and ledger accounts for ELM."""
from decimal import Decimal
from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel


class LeaveBalance(TimeStampedModel, UserScopedModel):
    """Annual leave entitlement and balance ledger per employee."""

    CATEGORY_CHOICES = [
        ("CL", "Casual Leave"),
        ("RH", "Restricted Holiday"),
        ("SCL", "Special Casual Leave"),
        ("EL", "Earned Leave"),
        ("VL", "Vacation Leave"),
        ("COL", "Commuted Leave"),
    ]

    year = models.IntegerField(db_index=True)
    category = models.CharField(max_length=8, choices=CATEGORY_CHOICES)
    credited_balance = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    carried_forward = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))
    availed_balance = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        db_table = "elm_leave_balance"
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "year", "category"],
                name="elm_unique_user_year_category",
            )
        ]
        indexes = [
            models.Index(fields=["user_id", "year"], name="elm_balance_user_year_idx"),
        ]

    @property
    def available_balance(self) -> Decimal:
        return self.credited_balance + self.carried_forward - self.availed_balance

    def __str__(self) -> str:
        return f"User {self.user_id} - {self.category} ({self.year}): Avail {self.available_balance}"


class LeaveAccountTransaction(TimeStampedModel, UserScopedModel):
    """Audit log of balance changes (credit, deduction, refund, conversion)."""

    TRANSACTION_TYPES = [
        ("credit", "Annual Credit"),
        ("deduction", "Leave Sanction Deduction"),
        ("refund", "Cancellation/Withdrawal Refund"),
        ("conversion", "Year-End VL to EL Conversion"),
    ]

    year = models.IntegerField(db_index=True)
    category = models.CharField(max_length=8)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    days = models.DecimalField(max_digits=5, decimal_places=2)
    remarks = models.CharField(max_length=255, blank=True)

    class Meta:
        db_table = "elm_leave_transaction"
        indexes = [
            models.Index(fields=["user_id", "year", "category"], name="elm_tx_user_year_cat_idx"),
        ]

    def __str__(self) -> str:
        return f"User {self.user_id} - {self.transaction_type} {self.days} {self.category}"
