"""The balance ledger — append-only, corrections are reversing entries (BR-06).

No balance column exists anywhere: the balance is the sum of these rows, which
is what makes a disputed figure explainable line by line.
"""
from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel, UserScopedModel

KIND_GRANT = "grant"
KIND_DEBIT = "debit"
KIND_CREDIT = "credit"
KIND_REVERSAL = "reversal"


class LeaveBalanceEntry(TimeStampedModel, UserScopedModel):
    """One signed movement in one (person, leave type, year) bucket."""

    KIND = [
        (KIND_GRANT, "Annual grant"),
        (KIND_DEBIT, "Debited by an approved leave"),
        (KIND_CREDIT, "Adjustment credit"),
        (KIND_REVERSAL, "Reversal of a debit"),
    ]

    leave_type = models.ForeignKey("elm.LeaveType", on_delete=models.PROTECT,
                                   related_name="balance_entries")
    year = models.PositiveSmallIntegerField()
    kind = models.CharField(max_length=12, choices=KIND)
    #: Signed: grants and credits positive, a debit negative.
    days = models.DecimalField(max_digits=5, decimal_places=1)
    application = models.ForeignKey("elm.LeaveApplication", null=True, blank=True,
                                    on_delete=models.PROTECT,
                                    related_name="balance_entries")
    granted_by_user_id = models.IntegerField(null=True, blank=True)
    note = models.CharField(max_length=300, blank=True)

    class Meta:
        db_table = "elm_leave_balance_entry"
        ordering = ["-created_at", "-id"]
        constraints = [
            models.CheckConstraint(condition=~Q(days=0),
                                   name="leave_entry_days_nonzero"),
            # The annual accrual is idempotent at the database, not by convention.
            models.UniqueConstraint(fields=["user_id", "leave_type", "year"],
                                    condition=Q(kind=KIND_GRANT),
                                    name="leave_grant_once_per_year"),
            # A retried approval still debits exactly once.
            models.UniqueConstraint(fields=["application"],
                                    condition=Q(kind=KIND_DEBIT),
                                    name="leave_debit_once_per_application"),
        ]
        indexes = [
            models.Index(fields=["user_id", "leave_type", "year"],
                         name="leave_entry_bucket_idx"),
        ]

    def __str__(self) -> str:
        return f"ledger#{self.pk} u{self.user_id} {self.kind} {self.days}"
