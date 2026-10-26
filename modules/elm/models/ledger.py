"""The leave account: an append-only ledger, never a balance column."""
from django.db import models

from core.db.mixins import UserScopedModel


class LedgerEntry(UserScopedModel):
    ANNUAL_CREDIT = "annual_credit"
    DEBIT = "debit"
    REVERSAL = "reversal"
    RESTORE = "restore"
    LAPSE = "lapse"
    CONVERSION_OUT = "conversion_out"
    CONVERSION_IN = "conversion_in"
    CARRY_FORWARD = "carry_forward"
    OFFLINE_DEBIT = "offline_debit"
    TYPES = [(t, t.replace("_", " ")) for t in (
        ANNUAL_CREDIT, DEBIT, REVERSAL, RESTORE, LAPSE, CONVERSION_OUT,
        CONVERSION_IN, CARRY_FORWARD, OFFLINE_DEBIT)]

    category = models.CharField(max_length=4)
    entry_type = models.CharField(max_length=16, choices=TYPES)
    delta = models.DecimalField(max_digits=7, decimal_places=2)
    year = models.PositiveSmallIntegerField()
    request = models.ForeignKey("LeaveRequest", null=True, blank=True,
                                on_delete=models.PROTECT, related_name="ledger")
    note = models.CharField(max_length=300, blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "elm_ledger_entry"
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "category", "year", "entry_type"],
                condition=models.Q(entry_type__in=[
                    "annual_credit", "lapse", "conversion_out", "conversion_in",
                    "carry_forward"]),
                name="elm_ledger_once_per_year"),
            models.UniqueConstraint(
                fields=["request", "entry_type"],
                condition=models.Q(request__isnull=False),
                name="elm_ledger_once_per_request"),
        ]
        indexes = [models.Index(fields=["user_id", "category"], name="elm_ledger_user_idx")]

    def __str__(self) -> str:
        return f"u{self.user_id} {self.category} {self.entry_type} {self.delta}"


class YearEndRun(models.Model):
    year = models.PositiveSmallIntegerField(unique=True)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    employees = models.PositiveIntegerField(default=0)
    exceptions = models.JSONField(default=list)

    class Meta:
        db_table = "elm_year_end_run"

    def __str__(self) -> str:
        return f"year-end {self.year}"
