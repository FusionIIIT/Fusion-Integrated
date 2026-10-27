from django.contrib.auth.models import User
from django.db import models


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