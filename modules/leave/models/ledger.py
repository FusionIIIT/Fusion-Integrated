"""Balances as an append-only ledger; corrections are new entries, never edits."""
from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel
from modules.leave.models.configuration import CATEGORY_CHOICES


class LeaveAccount(TimeStampedModel):
    """One row per employee: the lock every balance-affecting write takes first."""

    user_id = models.IntegerField(unique=True)
    employee_kind = models.CharField(max_length=10, blank=True)

    class Meta:
        db_table = "leave_account"

    def __str__(self) -> str:
        return f"account u{self.user_id}"


class LedgerEntry(models.Model):
    ENTRY_TYPES = [
        ("credit", "Annual credit"), ("debit", "Leave availed"),
        ("reversal", "Restored"), ("adjustment", "Administrative adjustment"),
        ("lapse", "Lapsed at year end"), ("carry_out", "Carried forward (closing)"),
        ("carry_in", "Carried forward (opening)"), ("convert_out", "Converted at year end"),
        ("convert_in", "Converted from VL"),
    ]

    user_id = models.IntegerField()
    leave_year = models.PositiveSmallIntegerField()
    category = models.CharField(max_length=4, choices=CATEGORY_CHOICES)
    delta = models.DecimalField(max_digits=7, decimal_places=2)
    entry_type = models.CharField(max_length=12, choices=ENTRY_TYPES)
    request = models.ForeignKey("leave.LeaveRequest", on_delete=models.PROTECT, null=True,
                                blank=True, related_name="ledger_entries")
    #: The same business fact always produces the same key, so a retry cannot post twice.
    idempotency_key = models.CharField(max_length=120, unique=True)
    note = models.CharField(max_length=300, blank=True)
    created_by_user_id = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "leave_ledger_entry"
        ordering = ["created_at", "id"]
        constraints = [models.CheckConstraint(condition=~Q(delta=0), name="leave_ledger_nonzero")]
        indexes = [models.Index(fields=["user_id", "leave_year", "category"],
                                name="leave_ledger_balance_idx")]

    def __str__(self) -> str:
        return f"u{self.user_id} {self.leave_year} {self.category} {self.delta:+}"
