"""Every movement of leave balance, as an append-only ledger."""
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

    #: The request this movement belongs to, where one applies.
    request_id = models.IntegerField(null=True, blank=True, db_index=True)
    #: The policy version this was computed under, so it can be re-derived.
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
            # A year's entitlement is credited once per category.
            models.UniqueConstraint(
                fields=["user_id", "year", "category"],
                condition=models.Q(reason="ANNUAL_CREDIT"),
                name="leave_ledger_one_annual_credit",
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


class YearEndClosure(TimeStampedModel, UserScopedModel):
    """That a leave year was settled for somebody, recorded once."""

    year = models.IntegerField(db_index=True)
    policy_id = models.IntegerField(null=True, blank=True)
    lapsed = models.DecimalField(max_digits=9, decimal_places=2, default=0)
    carried = models.DecimalField(max_digits=9, decimal_places=2, default=0)
    converted_vl = models.DecimalField(max_digits=9, decimal_places=2, default=0)
    el_from_conversion = models.DecimalField(max_digits=9, decimal_places=2, default=0)
    closed_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "leave_year_end_closure"
        ordering = ["user_id", "year"]
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "year"], name="leave_year_closed_once"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.user_id} closed {self.year}"
