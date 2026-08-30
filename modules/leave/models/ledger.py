"""Every movement of leave balance, as an append-only ledger.

There is no balance column anywhere in this module. A balance is the sum of
this table, which means it can always be recomputed, always explained entry by
entry, and cannot silently drift the way a counter edited from several places
eventually does. A wrong entry is corrected by a reversing entry, so the record
of what happened survives the correction.

This is the choice most likely to matter in ten years: a disputed balance can
be answered from the rows rather than argued about.
"""
from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel
from modules.leave.models.policy import CATEGORY_CHOICES


class EntryReason(models.TextChoices):
    ANNUAL_CREDIT = "ANNUAL_CREDIT", "Annual credit"
    OPENING_BALANCE = "OPENING_BALANCE", "Carried forward from last year"
    CONSUMED = "CONSUMED", "Charged to an approved leave"
    RESTORED = "RESTORED", "Returned after early resumption"
    CANCELLED = "CANCELLED", "Returned after cancellation"
    LAPSED = "LAPSED", "Lapsed at year end"
    CONVERTED_OUT = "CONVERTED_OUT", "Converted to another category"
    CONVERTED_IN = "CONVERTED_IN", "Received from a conversion"
    OFFLINE_RECORDED = "OFFLINE_RECORDED", "Recorded from an offline sanction"
    CORRECTION = "CORRECTION", "Administrative correction"


class LedgerEntry(TimeStampedModel, UserScopedModel):
    """One movement. Positive adds to the balance, negative takes from it."""

    year = models.IntegerField(db_index=True)
    category = models.CharField(max_length=8, choices=CATEGORY_CHOICES)
    days = models.DecimalField(max_digits=7, decimal_places=2)
    reason = models.CharField(max_length=24, choices=EntryReason.choices)

    #: The request this movement belongs to, where one applies. A plain integer
    #: for consistency with the module's other cross-references.
    request_id = models.IntegerField(null=True, blank=True, db_index=True)
    #: The policy version the movement was computed under, so the arithmetic
    #: can be re-derived even after the policy changes.
    policy_id = models.IntegerField(null=True, blank=True)
    #: Set when this entry reverses an earlier one; the original is never edited.
    reverses_id = models.IntegerField(null=True, blank=True)
    recorded_by_user_id = models.IntegerField(null=True, blank=True)
    note = models.CharField(max_length=250, blank=True)

    class Meta:
        db_table = "leave_ledger_entry"
        ordering = ["user_id", "year", "category", "id"]
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(days=0), name="leave_ledger_no_zero_entry"
            ),
        ]
        indexes = [
            models.Index(
                fields=["user_id", "year", "category"], name="leave_ledger_balance_idx"
            ),
            models.Index(fields=["request_id"], name="leave_ledger_request_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} {self.year} {self.category} {self.days:+}"
