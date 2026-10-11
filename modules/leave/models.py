from django.db import models
from fusion_auth.models import UserRef

class LeaveApplication(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    LEAVE_TYPE_CHOICES = [
        ('CL', 'Casual Leave'),
        ('RH', 'Restricted Holiday'),
        ('SCL', 'Special Casual Leave'),
        ('EL', 'Earned Leave'),
        ('COL', 'Compensatory Off Leave'),
        ('VL', 'Vacation Leave'),
    ]

    employee = models.ForeignKey(UserRef, on_delete=models.CASCADE)
    leave_type = models.CharField(max_length=3, choices=LEAVE_TYPE_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')

    class Meta:
        db_table = 'leave_application'
