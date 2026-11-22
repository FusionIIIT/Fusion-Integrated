"""Charge for an approved special food request (BR-MMS-030;
UC-020/030; BW-MMS-13/14/15, CW-MMS-05)."""

from django.db import models

from core.db.mixins import TimeStampedModel


class SpecialFoodCharge(TimeStampedModel):
    request = models.IntegerField(db_index=True)
    student_user_id = models.IntegerField(db_index=True)
    month = models.DateField(db_index=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = "mms_special_food_charge"
        indexes = [
            models.Index(fields=["student_user_id", "month"], name="sf_charge_student_month_idx"),
        ]

    def __str__(self) -> str:
        return f"charge:{self.request}:{self.month}:{self.amount}"
