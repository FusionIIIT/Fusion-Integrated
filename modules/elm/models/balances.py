from decimal import Decimal
from django.db import models
from core.db.mixins import TimeStampedModel, UserScopedModel


class EmployeeLeaveBalance(TimeStampedModel, UserScopedModel):
    year = models.IntegerField(db_index=True)
    leave_category = models.CharField(max_length=8)
    allocated_days = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.0"))
    availed_days = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.0"))
    carried_forward = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.0"))
    pending_days = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.0"))

    class Meta:
        db_table = "elm_employee_leave_balance"
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "year", "leave_category"],
                name="elm_balance_unique_user_year_cat",
            ),
        ]
        indexes = [
            models.Index(fields=["user_id", "year"], name="elm_balance_user_year_idx"),
        ]

    @property
    def available_days(self) -> Decimal:
        return self.allocated_days + self.carried_forward - self.availed_days - self.pending_days

    def __str__(self) -> str:
        return f"u{self.user_id} {self.leave_category} ({self.year}): avail={self.available_days}"


class YearEndTransaction(TimeStampedModel, UserScopedModel):
    year = models.IntegerField(db_index=True)
    leave_category = models.CharField(max_length=8)
    closing_balance = models.DecimalField(max_digits=5, decimal_places=2)
    lapsed_days = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.0"))
    converted_to_el = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.0"))
    carried_forward = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0.0"))

    class Meta:
        db_table = "elm_year_end_transaction"
