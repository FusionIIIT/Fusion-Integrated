"""Balances, the append-only account ledger, and year-end run records.

Balances are materialised rows (BR-EL-002…009, CFR-EL-003.5) so a deduction
can be made under `select_for_update` inside the approval transaction;
the ledger is the immutable evidence behind every number.
"""
from __future__ import annotations

from django.db import models

from core.db.mixins import TimeStampedModel


class LeaveBalance(TimeStampedModel):
    """One employee's balance in one category for one leave year.

    available = carried_forward + credited + adjusted - used
    """

    user_id = models.IntegerField(db_index=True)
    category = models.CharField(max_length=8)
    year = models.PositiveSmallIntegerField()

    carried_forward = models.DecimalField(max_digits=6, decimal_places=2,
                                          default=0)   # from prior year
    credited = models.DecimalField(max_digits=6, decimal_places=2,
                                   default=0)          # annual entitlement
    used = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    adjusted = models.DecimalField(max_digits=6, decimal_places=2,
                                   default=0)          # signed: admin, lapse

    class Meta:
        db_table = "leave_balance"
        constraints = [
            models.UniqueConstraint(fields=["user_id", "category", "year"],
                                    name="leave_balance_unique"),
        ]

    def __str__(self) -> str:
        return f"user {self.user_id} {self.category.upper()} {self.year}"

    @property
    def available(self) -> float:
        from decimal import Decimal
        total = (self.carried_forward + self.credited + self.adjusted
                 - self.used)
        return float(total)


class LeaveAccountTransaction(TimeStampedModel):
    """One immutable balance mutation (CFR-EL-003.5): approvals, cancellations,
    extensions, resumption refunds, admin adjustments, year-end outcomes."""

    CREDIT = "credit"                    # annual entitlement / carry-in
    DEDUCTION = "deduction"              # approved leave consumed
    CANCELLATION_RESTORATION = "cancellation_restoration"
    EXTENSION_DEDUCTION = "extension_deduction"
    REFUND = "refund"                    # resumption: returned early
    ADMIN_ADJUSTMENT = "admin_adjustment"
    CARRY_FORWARD = "carry_forward"
    VL_TO_EL_CONVERSION = "vl_to_el_conversion"
    YEAR_END_LAPSE = "year_end_lapse"
    KIND = [(CREDIT, "Credit"), (DEDUCTION, "Deduction"),
            (CANCELLATION_RESTORATION, "Cancellation restoration"),
            (EXTENSION_DEDUCTION, "Extension deduction"),
            (REFUND, "Refund"), (ADMIN_ADJUSTMENT, "Admin adjustment"),
            (CARRY_FORWARD, "Carry forward"),
            (VL_TO_EL_CONVERSION, "VL to EL conversion"),
            (YEAR_END_LAPSE, "Year-end lapse")]

    user_id = models.IntegerField(db_index=True)
    category = models.CharField(max_length=8)
    year = models.PositiveSmallIntegerField()
    kind = models.CharField(max_length=32, choices=KIND)
    days = models.DecimalField(max_digits=6, decimal_places=2)  # signed
    request = models.ForeignKey("LeaveRequest", null=True, blank=True,
                                on_delete=models.SET_NULL,
                                related_name="transactions")
    note = models.CharField(max_length=300, blank=True)
    actor_user_id = models.IntegerField(null=True, blank=True)
    at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "leave_account_transaction"
        ordering = ["-at"]

    def __str__(self) -> str:
        return f"{self.kind} {self.days} {self.category.upper()}"


class LeaveYearRun(TimeStampedModel):
    """Idempotency marker for the year-end sweep: one row per leave year."""

    year = models.PositiveSmallIntegerField(unique=True)
    processed_at = models.DateTimeField(auto_now_add=True)
    report = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "leave_year_run"
        ordering = ["-year"]

    def __str__(self) -> str:
        return f"year-end {self.year}"
