from django.db import models

from core.db.mixins import TimeStampedModel
from modules.patents.models.application import PatentApplication

ENTRY_KINDS = ("REQUEST", "APPROVAL", "ESCALATION", "REVERSAL", "DISBURSEMENT")


class AppendOnlyViolation(Exception):
    """Raised when code tries to change or delete a row that must never change."""


class PatentBudgetLedger(TimeStampedModel):
    """Append-only budget ledger (R1-08).

    A request is recorded once as REQUEST. A decision is a new APPROVAL or ESCALATION row
    whose replaces_entry points at the request. A correction is a new REVERSAL row whose
    replaces_entry points at the approval it reverses. Rows are never updated or deleted.
    """

    application = models.ForeignKey(
        PatentApplication,
        on_delete=models.CASCADE,
        related_name="budget_entries",
    )
    entry_kind = models.CharField(
        max_length=20,
        choices=[(k, k) for k in ENTRY_KINDS],
        default="REQUEST",
    )
    replaces_entry = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="linked_entries",
    )
    entry_type = models.CharField(max_length=30)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default="INR")
    category = models.CharField(max_length=50)
    status = models.CharField(max_length=30, default="PENDING")
    authorized_by_user_id = models.IntegerField(db_index=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "patents_budget_ledger"

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise AppendOnlyViolation("Budget ledger rows are append-only; record a new entry.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise AppendOnlyViolation("Budget ledger rows are append-only; record a reversal.")
