from django.db import models
from django.db.models import Q
from core.db.mixins import TimeStampedModel
from modules.elm.models.leave_types import LeaveType


class LeaveBalance(TimeStampedModel):
    """Leave balance record for an employee per leave category and calendar year.

    Implements BR-EL-002, BR-EL-005, BR-EL-007, BR-EL-009, BR-EL-028.
    Uses DecimalField so fractional conversions (e.g. VL-to-EL) are accurately represented.
    """
    employee_user_id = models.IntegerField(db_index=True)
    leave_type = models.ForeignKey(
        LeaveType, on_delete=models.PROTECT, related_name="balances"
    )
    year = models.PositiveSmallIntegerField(db_index=True)
    credited = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)
    used = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)

    class Meta:
        db_table = "elm_leave_balance"
        constraints = [
            models.UniqueConstraint(
                fields=["employee_user_id", "leave_type", "year"],
                name="unique_employee_leave_year",
            ),
            models.CheckConstraint(
                condition=Q(credited__gte=0) & Q(used__gte=0),
                name="non_negative_balance_values",
            ),
        ]
        indexes = [
            models.Index(
                fields=["employee_user_id", "year"],
                name="employee_year_balance_idx",
            ),
        ]

    @property
    def remaining(self):
        return self.credited - self.used

    def __str__(self):
        return f"Balance for user {self.employee_user_id} - {self.leave_type.code} ({self.year}): {self.remaining}"
