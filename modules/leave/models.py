from django.db import models
from core.db.mixins import TimeStampedModel, UserScopedModel


class LeaveType(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    def __str__(self) -> str:
        return self.name


class LeaveBalance(TimeStampedModel, UserScopedModel):
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    balance = models.IntegerField(default=0)

    def __str__(self) -> str:
        return f"User {self.user_id} - {self.leave_type.name}: {self.balance}"


class LeaveApplication(TimeStampedModel, UserScopedModel):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')

    def __str__(self) -> str:
        return f"Application {self.id} (User {self.user_id}): {self.status}"
