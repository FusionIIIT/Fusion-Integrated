"""The leave account: append-only, so a balance is a sum, never a column."""
from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel, UserScopedModel
from modules.elm.models.requests import CATEGORY_CHOICES, LeaveRequest


class LedgerEntry(TimeStampedModel, UserScopedModel):
    ANNUAL_CREDIT = "annual_credit"
    DEBIT = "debit"
    RESTORE = "restore"
    CARRY_FORWARD = "carry_forward"
    LAPSE = "lapse"
    CONVERSION_OUT = "conversion_out"
    CONVERSION_IN = "conversion_in"
    ADJUSTMENT = "adjustment"
    KIND = [(k, k.replace("_", " ").title()) for k in (
        ANNUAL_CREDIT, DEBIT, RESTORE, CARRY_FORWARD, LAPSE, CONVERSION_OUT,
        CONVERSION_IN, ADJUSTMENT)]
    #: At most one of each per person, category and year; year-end reruns are no-ops.
    ONCE_A_YEAR = (ANNUAL_CREDIT, CARRY_FORWARD, LAPSE, CONVERSION_OUT,
                   CONVERSION_IN)

    category = models.CharField(max_length=3, choices=CATEGORY_CHOICES)
    year = models.PositiveSmallIntegerField()
    kind = models.CharField(max_length=16, choices=KIND)
    days = models.DecimalField(max_digits=6, decimal_places=1)
    request = models.ForeignKey(LeaveRequest, null=True, blank=True,
                                on_delete=models.PROTECT, related_name="ledger")
    note = models.CharField(max_length=300, blank=True)
    recorded_by_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "elm_ledger_entry"
        ordering = ["year", "created_at", "id"]
        indexes = [models.Index(fields=["user_id", "category", "year"],
                                name="elm_ledger_account_idx")]
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "category", "year", "kind"],
                condition=Q(kind__in=["annual_credit", "carry_forward", "lapse",
                                      "conversion_out", "conversion_in"]),
                name="elm_ledger_once_a_year"),
        ]
