"""Leave accounts and the append-only ledger that gives them a balance.

There is deliberately no balance column: a balance can be edited, and a
correction to it is invisible afterwards. Every movement here is a row, so the
year-end run, an approval and a reversal all read the same way.
"""

from decimal import Decimal

from django.db import models

from core.db.mixins import TimeStampedModel
from modules.leave.domain import ledger as led


class LeaveAccount(TimeStampedModel):
    """One person, one leave category, one calendar year."""

    user_id = models.IntegerField(db_index=True)
    year = models.PositiveSmallIntegerField()
    category = models.CharField(max_length=4)

    class Meta:
        db_table = "leave_account"
        ordering = ["user_id", "year", "category"]
        constraints = [
            models.UniqueConstraint(fields=["user_id", "year", "category"],
                                    name="leave_account_unique"),
        ]

    def balance(self) -> Decimal:
        return led.project(
            self.entries.values_list("entry_type", "days").order_by("id"))

    def __str__(self) -> str:
        return f"u{self.user_id} {self.year} {self.category}"


class LeaveLedgerEntry(TimeStampedModel):
    """An append-only movement. A correction is another row, never an edit."""

    account = models.ForeignKey(LeaveAccount, on_delete=models.CASCADE,
                                related_name="entries")
    entry_type = models.CharField(
        max_length=16, choices=[(t, t.replace("_", " ")) for t in led.ENTRY_TYPES])
    days = models.DecimalField(max_digits=6, decimal_places=2)
    #: What caused it: a request id, a year, a year-end run, an adjustment.
    reference = models.CharField(max_length=64, blank=True)
    reason = models.CharField(max_length=300, blank=True)
    actor_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "leave_ledger_entry"
        ordering = ["id"]
        indexes = [
            models.Index(fields=["account", "entry_type"],
                         name="leave_ledger_account_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.entry_type} {self.days} on {self.account_id}"
