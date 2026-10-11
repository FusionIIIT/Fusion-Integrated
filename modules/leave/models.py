from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel


class LeaveBalance(UserScopedModel, TimeStampedModel):
    leave_type = models.CharField(max_length=10, choices=[
        ('CL', 'Casual Leave'),
        ('RH', 'Restricted Holiday'),
        ('SCL', 'Special Casual Leave'),
        ('EL', 'Earned Leave'),
        ('VL', 'Vacation Leave'),
        ('COL', 'Commuted Leave')
    ])
    year = models.IntegerField()
    allocated = models.DecimalField(max_digits=10, decimal_places=2)
    used = models.DecimalField(max_digits=10, decimal_places=2)


class LeaveApplication(UserScopedModel, TimeStampedModel):
    leave_type = models.CharField(max_length=10, choices=[
        ('CL', 'Casual Leave'),
        ('RH', 'Restricted Holiday'),
        ('SCL', 'Special Casual Leave'),
        ('EL', 'Earned Leave'),
        ('VL', 'Vacation Leave'),
        ('COL', 'Commuted Leave')
    ])
    start_date = models.DateField()
    end_date = models.DateField()
    half_day = models.CharField(max_length=15, choices=[
        ('NONE', 'None'),
        ('FIRST_HALF', 'First Half'),
        ('SECOND_HALF', 'Second Half')
    ], default='NONE')
    days = models.DecimalField(max_digits=5, decimal_places=2)
    reason = models.TextField()
    is_station_leave = models.BooleanField(default=False)
    station_leave_address = models.TextField(blank=True)
    replacement_user_id = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=[
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('CANCELLED', 'Cancelled')
    ], default='PENDING')
    reviewed_by = models.IntegerField(null=True, blank=True)
    review_remarks = models.TextField(blank=True)
