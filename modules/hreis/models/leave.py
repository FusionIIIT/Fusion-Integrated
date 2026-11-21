"""Append-only leave credits, deductions and explicit reversals."""

from django.db import models
from django.db.models import Q


class LeaveLedgerEntry(models.Model):
    user_id = models.IntegerField()
    leave_type = models.CharField(max_length=40)
    quantity = models.DecimalField(max_digits=18, decimal_places=4)
    request = models.ForeignKey(
        "HRRequest", on_delete=models.PROTECT, null=True, blank=True, related_name="leave_entries"
    )
    policy_version = models.ForeignKey(
        "HRPolicyVersion", on_delete=models.PROTECT, related_name="leave_entries"
    )
    event_key = models.CharField(max_length=120, unique=True)
    reversing = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True, related_name="reversals"
    )
    actor_user_id = models.IntegerField(null=True, blank=True)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "hreis_leave_ledger"
        constraints = [
            models.CheckConstraint(condition=~Q(quantity=0), name="hr_ledger_nonzero"),
            models.UniqueConstraint(
                fields=["reversing"],
                condition=Q(reversing__isnull=False),
                name="hr_ledger_one_reversal",
            ),
        ]
        indexes = [
            models.Index(
                fields=["user_id", "leave_type", "recorded_at"], name="hr_leave_balance_idx"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.leave_type} ledger entry {self.pk}"
