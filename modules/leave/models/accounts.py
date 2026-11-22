"""The leave account: an append-only ledger plus a balance the ledger projects.

The ledger is the record of truth and is never edited. A correction is a
reversing entry. The balance row exists so a balance lookup is one row, and it
is always written in the same transaction as the entries that move it, under a
row lock, so two concurrent postings cannot both read the same starting figure.
"""
from __future__ import annotations

from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from core.db.mixins import TimeStampedModel
from modules.leave.domain import categories as cat

# Ledger entry kinds. `reversal` points at the entry it undoes.
CREDIT = "credit"
DEBIT = "debit"
LAPSE = "lapse"
CARRY_FORWARD = "carry_forward"
CONVERSION = "conversion"
REVERSAL = "reversal"
ADJUSTMENT = "adjustment"

ENTRY_KINDS: tuple[str, ...] = (CREDIT, DEBIT, LAPSE, CARRY_FORWARD, CONVERSION,
                                REVERSAL, ADJUSTMENT)

#: Kinds that add to a balance. Everything else subtracts.
ADDITIVE: frozenset[str] = frozenset({CREDIT, CARRY_FORWARD, CONVERSION,
                                       ADJUSTMENT, REVERSAL})


class LeaveLedgerEntry(TimeStampedModel):
    """One immutable movement of leave entitlement."""
    user_id = models.IntegerField(db_index=True)
    year = models.PositiveSmallIntegerField(db_index=True)
    category = models.CharField(max_length=8, choices=[(c, c) for c in cat.CATEGORIES],
                                db_index=True)
    kind = models.CharField(max_length=24, choices=[(k, k) for k in ENTRY_KINDS])
    days = models.DecimalField(max_digits=8, decimal_places=2)
    note = models.CharField(max_length=300, blank=True, default="")
    #: The request that caused this movement, when one did.
    leave_request_id = models.IntegerField(null=True, blank=True, db_index=True)
    created_by_user_id = models.IntegerField(null=True, blank=True)
    #: Set only on a reversing entry, and never on the entry it undoes.
    reverses_id = models.IntegerField(null=True, blank=True, unique=True)

    class Meta:
        ordering = ("-id",)
        indexes = [models.Index(fields=("user_id", "year", "category"))]

    def __str__(self) -> str:
        return f"{self.user_id} {self.year} {self.category} {self.kind} {self.days}"

    @property
    def signed_days(self) -> Decimal:
        return self.days if self.kind in ADDITIVE else -self.days


class LeaveBalance(TimeStampedModel):
    """The projected balance. Never the source of truth; the ledger is."""
    user_id = models.IntegerField(db_index=True)
    year = models.PositiveSmallIntegerField()
    category = models.CharField(max_length=8, choices=[(c, c) for c in cat.CATEGORIES])
    days = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0"),
                               validators=[MinValueValidator(Decimal("-100000"))])
    #: Year-end processing credits each (user, year) once (BR-EL-002..009).
    year_end_applied = models.BooleanField(default=False)

    class Meta:
        ordering = ("user_id", "year", "category")
        constraints = [
            models.UniqueConstraint(fields=("user_id", "year", "category"),
                                    name="leave_balance_unique"),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} {self.year} {self.category} = {self.days}"