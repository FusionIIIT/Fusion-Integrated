from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class LeaveApplication(models.Model):
    STATUS_CHOICES = [
        ('AWAITING_UNIT_HEAD', 'Awaiting Unit Head'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
    ]

    applicant = models.ForeignKey(User, on_delete=models.CASCADE)
    category = models.CharField(max_length=10, default='CL')
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='AWAITING_UNIT_HEAD'
    )
    remarks = models.TextField(blank=True, null=True)

    class Meta:
        permissions = [
            ('can_approve', 'Can approve leave application'),
        ]


class LeaveBalance(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    year = models.IntegerField()
    casual_leave = models.IntegerField(default=0)


class LeaveBalanceHistory(models.Model):
    applicant = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='balance_histories'
    )
    leave_application = models.ForeignKey(
        'LeaveApplication', on_delete=models.CASCADE, related_name='histories'
    )
    category = models.CharField(max_length=10)
    previous_balance = models.IntegerField()
    new_balance = models.IntegerField()
    action_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='performed_actions',
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    action = models.CharField(max_length=20, default='DEDUCT')

    def __str__(self):
        return f'{self.applicant.username} - {self.category}: {self.previous_balance} -> {self.new_balance}'