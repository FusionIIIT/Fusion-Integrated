from django.db import models
from core.db.mixins import TimeStampedModel, UserScopedModel

class LeaveBalance(TimeStampedModel, UserScopedModel):
    year = models.PositiveSmallIntegerField(db_index=True)
    is_faculty = models.BooleanField(default=False)
    year_end_processed = models.BooleanField(default=False)

    cl_balance = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("8.00"))
    rh_balance = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("2.00"))
    scl_balance = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("15.00"))
    el_balance = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("30.00"))
    vl_balance = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("60.00"))
    col_balance = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("20.00"))

    class Meta:
        db_table = "leave_balance"
        constraints = [
            models.UniqueConstraint(fields=["user_id", "year"], name="leave_balance_unique_user_year")
        ]
        indexes = [
            models.Index(fields=["user_id"]),
            models.Index(fields=["year"])
        ]

    def get_category_balance(self, category: str) -> Decimal:
        return getattr(self, f"{category}_balance")

    def deduct(self, category: str, days: Decimal) -> None:
        setattr(self, f"{category}_balance", self.get_category_balance(category) - days)
        self.save()

    def credit(self, category: str, days: Decimal) -> None:
        setattr(self, f"{category}_balance", self.get_category_balance(category) + days)
        self.save()


class LeaveLedgerEntry(TimeStampedModel, UserScopedModel):
    balance = models.ForeignKey(LeaveBalance, on_delete=models.CASCADE, related_name="ledger_entries")
    category = models.CharField(max_length=10)
    entry_type = models.CharField(
        max_length=20,
        choices=[
            ("credit", "Annual Credit"),
            ("debit", "Leave Availment"),
            ("reversal", "Cancellation Reversal"),
            ("conversion", "VL to EL Conversion"),
            ("lapse", "Year-End Lapse"),
            ("adjustment", "Resumption Adjustment")
        ]
    )
    change_amount = models.DecimalField(max_digits=6, decimal_places=2)
    balance_after = models.DecimalField(max_digits=6, decimal_places=2)
    reference_id = models.IntegerField(null=True, blank=True)
    idempotency_key = models.CharField(max_length=120, blank=True, db_index=True)
    remarks = models.TextField(blank=True)

    class Meta:
        db_table = "leave_ledger_entry"
        ordering = ["-created_at"]