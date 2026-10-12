from django.db import models
from django.contrib.auth import get_user_model

class LeaveType(models.Model):
    type_name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.type_name

class LeaveBalance(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    balance = models.IntegerField()

    def __str__(self):
        return f"{self.user.username} - {self.leave_type.type_name}"

class LeaveRequest(models.Model):
    STATUS_PENDING = 'P'
    STATUS_APPROVED = 'A'
    STATUS_REJECTED = 'R'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
    ]

    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=1, choices=STATUS_CHOICES, default=STATUS_PENDING)

    def __str__(self):
        return f"{self.user.username} - {self.leave_type.type_name} - {self.start_date} - {self.end_date}"