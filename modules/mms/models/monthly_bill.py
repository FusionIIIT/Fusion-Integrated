"""Monthly bill (BR-MMS-016/017/018/019/030; UC-010/011/030; BW-MMS-16)."""

from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel, UserScopedModel


class MonthlyBill(TimeStampedModel, UserScopedModel):
    STATE = [("generated", "Generated"), ("finalized", "Finalized"), ("published", "Published")]

    month = models.DateField(db_index=True)
    state = models.CharField(max_length=16, choices=STATE, default="generated")
    served_day_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    special_meal_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    rebate_deductions = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    generated_at = models.DateTimeField(auto_now_add=True)
    finalized_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    finalized_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "mms_monthly_bill"
        indexes = [
            models.Index(fields=["user_id", "month"], name="monthly_bill_student_month_idx"),
            models.Index(fields=["state", "month"], name="monthly_bill_state_month_idx"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "month"],
                name="one_bill_per_student_per_month",
            ),
            models.CheckConstraint(
                condition=Q(total__gte=0),
                name="monthly_bill_total_non_negative",
            ),
        ]

    def __str__(self) -> str:
        return f"bill:{self.student_user_id}:{self.month}:{self.state}"
