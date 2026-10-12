"""The immutable leave ledger (blueprint Step 3.2).

Balances are *derived* by summing this table; there is no mutable balance
column. Rows are never updated — a correction is a new ``REVERSAL`` entry that
points at the row it reverses.

The ``ANNUAL_CREDIT`` partial unique is the idempotency mechanism (evidenced at
``testing-strategy.md:49-50``). It proves an annual credit for a given
``(user, leave_type, credit_year)`` is applied once; it does **not** decide
*when* credit is allocated, whether it is prorated, or how fractions round —
those remain unresolved (§3.8 #7).
"""
from django.db import models

from modules.leave.models.policy import LEAVE_TYPE_CHOICES


class LeaveLedgerEntry(models.Model):
    """One append-only ledger movement — CONVENTION + EXPLICIT mechanism."""

    ENTRY_KINDS = [
        ("ANNUAL_CREDIT", "Annual credit"),
        ("CONSUMED", "Consumed"),
        ("CARRY_FORWARD", "Carry forward"),
        ("LAPSE", "Lapse"),
        ("CONVERSION_OUT", "Conversion out"),
        ("CONVERSION_IN", "Conversion in"),
        ("CANCELLATION_RESTORE", "Cancellation restore"),
        ("OFFLINE_SYNC", "Offline synchronization"),
        ("ADJUSTMENT", "Adjustment"),
        ("REVERSAL", "Reversal"),
    ]

    user_id = models.IntegerField(db_index=True)
    leave_type = models.CharField(max_length=8, choices=LEAVE_TYPE_CHOICES)
    entry_kind = models.CharField(max_length=24, choices=ENTRY_KINDS)
    #: Signed: positive credits, negative consumption.
    days = models.DecimalField(max_digits=7, decimal_places=2)

    source_type = models.CharField(max_length=60, blank=True)
    source_id = models.IntegerField(null=True, blank=True)
    #: Null for movements not tied to a credit year (e.g. a mid-year adjustment).
    credit_year = models.PositiveSmallIntegerField(null=True, blank=True)
    #: Set on a REVERSAL row, pointing at the row it corrects.
    reversal_of = models.ForeignKey("self", null=True, blank=True,
                                    on_delete=models.PROTECT, related_name="+")

    created_at = models.DateTimeField(auto_now_add=True)
    created_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "leave_ledger_entry"
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "leave_type", "credit_year"],
                condition=models.Q(entry_kind="ANNUAL_CREDIT"),
                name="leave_annual_credit_once",
            ),
        ]
        indexes = [
            models.Index(fields=["user_id", "leave_type"],
                         name="leave_ledger_user_type_idx"),
            models.Index(fields=["entry_kind", "credit_year"],
                         name="leave_ledger_kind_year_idx"),
        ]

    def __str__(self) -> str:
        return f"ledger u{self.user_id} {self.leave_type} {self.entry_kind} {self.days}"
