from django.db import models
from core.db.mixins import TimeStampedModel, UserScopedModel

class LeaveType(TimeStampedModel, UserScopedModel):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    class Meta:
        db_table = "elm_leave_type"

class LeaveRequest(TimeStampedModel, UserScopedModel):
    STATUS = [
        ("draft", "Draft"), ("submitted", "Submitted"),
        ("approved", "Approved"), ("rejected", "Rejected"),
    ]

    user = models.ForeignKey("core.User", on_delete=models.CASCADE)
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(max_length=24, choices=STATUS, default="draft")

    class Meta:
        db_table = "elm_leave_request"

class LeaveBalance(TimeStampedModel, UserScopedModel):
    user = models.ForeignKey("core.User", on_delete=models.CASCADE)
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = "elm_leave_balance"
        constraints = [
            models.UniqueConstraint(fields=["user", "leave_type"],
                                    name="leave_balance_unique_per_user_type"),
        ]
