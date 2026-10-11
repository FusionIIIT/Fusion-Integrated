"""Leave balances and auditable balance ledger."""

from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel


class LeaveBalance(TimeStampedModel):
    LEAVE_TYPES = [
        ("CL", "Casual Leave"),
        ("RH", "Restricted Holiday"),
        ("SCL", "Special Casual Leave"),
        ("EL", "Earned Leave"),
        ("COL", "Compensatory Leave"),
        ("VL", "Vacation Leave"),
    ]

    user_id = models.IntegerField(db_index=True)
    leave_year = models.PositiveSmallIntegerField()
    leave_type = models.CharField(max_length=3, choices=LEAVE_TYPES)

    # Decimal amounts preserve half-days and fractional conversions.
    opening_balance = models.DecimalField(
        max_digits=7, decimal_places=2, default=0
    )
    annual_entitlement = models.DecimalField(
        max_digits=7, decimal_places=2, default=0
    )
    accrued = models.DecimalField(
        max_digits=7, decimal_places=2, default=0
    )
    used = models.DecimalField(
        max_digits=7, decimal_places=2, default=0
    )

    class Meta:
        db_table = "elm_leave_balance"
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "leave_year", "leave_type"],
                name="elm_balance_user_year_type",
            ),
            models.CheckConstraint(
                condition=Q(opening_balance__gte=0),
                name="elm_balance_opening_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(annual_entitlement__gte=0),
                name="elm_balance_entitlement_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(accrued__gte=0),
                name="elm_balance_accrued_nonnegative",
            ),
            models.CheckConstraint(
                condition=Q(used__gte=0),
                name="elm_balance_used_nonnegative",
            ),
        ]
        indexes = [
            models.Index(
                fields=["user_id", "leave_year"],
                name="elm_balance_user_year",
            ),
        ]

    @property
    def available_balance(self):
        return (
            self.opening_balance
            + self.annual_entitlement
            + self.accrued
            - self.used
        )

    def __str__(self):
        return (
            f"user {self.user_id} {self.leave_type} "
            f"{self.leave_year}: {self.available_balance}"
        )


class LeaveLedgerEntry(TimeStampedModel):
    ENTRY_TYPES = [
        ("credit", "Credit"),
        ("debit", "Debit"),
        ("adjustment", "Adjustment"),
        ("conversion", "Year-end Conversion"),
    ]

    balance = models.ForeignKey(
        LeaveBalance,
        on_delete=models.PROTECT,
        related_name="ledger_entries",
    )
    entry_type = models.CharField(max_length=12, choices=ENTRY_TYPES)
    amount = models.DecimalField(max_digits=7, decimal_places=2)
    reference_key = models.CharField(max_length=120, blank=True)
    description = models.CharField(max_length=300, blank=True)
    actor_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "elm_leave_ledger_entry"
        ordering = ["created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__gt=0),
                name="elm_ledger_amount_positive",
            ),
            models.UniqueConstraint(
                fields=["balance", "reference_key"],
                condition= ~Q(reference_key=""),
                name="elm_ledger_ref_unique",
            ),
        ]
        indexes = [
            models.Index(
                fields=["balance", "created_at"],
                name="elm_ledger_balance_time",
            ),
        ]

    def __str__(self):
        return f"{self.entry_type} {self.amount} for balance #{self.balance_id}"
