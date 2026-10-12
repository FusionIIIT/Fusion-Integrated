from django.db import models

from core.db.mixins import TimeStampedModel
from modules.directory.models import UserRef


class LeaveCategory(TimeStampedModel):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    class Meta:
        db_table = "elm_leave_category"
        verbose_name_plural = "Leave Categories"

    def __str__(self) -> str:
        return self.name


class LeaveApplication(TimeStampedModel):
    employee = models.ForeignKey(UserRef, on_delete=models.CASCADE, related_name="leave_applications")
    category = models.ForeignKey(LeaveCategory, on_delete=models.CASCADE, related_name="applications")
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=[("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected")], default="pending")

    class Meta:
        db_table = "elm_leave_application"
        verbose_name_plural = "Leave Applications"

    def __str__(self) -> str:
        return f"{self.employee} - {self.category} - {self.status}"


class LeaveBalance(TimeStampedModel):
    employee = models.ForeignKey(UserRef, on_delete=models.CASCADE, related_name="leave_balances")
    category = models.ForeignKey(LeaveCategory, on_delete=models.CASCADE, related_name="balances")
    balance = models.IntegerField()

    class Meta:
        db_table = "elm_leave_balance"
        verbose_name_plural = "Leave Balances"

    def __str__(self) -> str:
        return f"{self.employee} - {self.category} - {self.balance}"
