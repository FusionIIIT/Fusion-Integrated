from django.db import models
from django.contrib.auth.models import User

LEAVE_STATUS = (
    ('PENDING', 'Pending'),
    ('APPROVED', 'Approved'),
    ('REJECTED', 'Rejected'),
)

class LeaveType(models.Model):
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name

class LeaveBalance(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    leave_type = models.ForeignKey(LeaveType,
on_delete=models.CASCADE)
    balance = models.IntegerField()

    def __str__(self):
        return f'{self.user.username} - {self.leave_type.name}'

class LeaveApplication(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    substitute = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='substitute',
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=20,
        choices=LEAVE_STATUS,
        default='PENDING',
    )

    def __str__(self):
        return f'{self.user.username} - {self.leave_type.name} from {self.start_date} to {self.end_date}'