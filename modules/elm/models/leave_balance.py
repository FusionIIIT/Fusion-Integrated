from django.db import models
from django.utils.translation import gettext as _

class LeaveBalance(models.Model):
    user_id = models.IntegerField()
    leave_type = models.ForeignKey("LeaveType", on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = "elm_leave_balance"
        ordering = ["user_id", "leave_type"]
        indexes = [
            models.Index(fields=["user_id"], name="leave_balance_user_idx"),
            models.Index(fields=["leave_type"], name="leave_balance_type_idx"),
        ]

    def __str__(self):
        return f"LeaveBalance for user {self.user_id} and type {self.leave_type}"

    class LeaveType(models.TextChoices):
        FULL_DAY = "FD", _("Full Day")
        HALF_DAY = "HD", _("Half Day")

    leave_type = models.ForeignKey("LeaveType", on_delete=models.CASCADE, choices=LeaveType.choices)
