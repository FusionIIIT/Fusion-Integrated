from django.db import models
from django.utils import timezone
from datetime import datetime
from fusion_auth.principal import Principal

from core.db.mixins import TimeStampedModel


class LeaveType(models.Model):
    CL = 'CL'
    RH = 'RH'
    SCL = 'SCL'
    EL = 'EL'
    COL = 'COL'
    VL = 'VL'
    STATION_LEAVE = 'STATION_LEAVE'

    TYPE_CHOICES = [
        (CL, 'Casual Leave'),
        (RH, 'Restricted Holiday'),
        (SCL, 'Special Casual Leave'),
        (EL, 'Earned Leave'),
        (COL, 'Caregiver Leave'),
        (VL, 'Vacation Leave'),
        (STATION_LEAVE, 'Station Leave'),
    ]

    type = models.CharField(max_length=3, choices=TYPE_CHOICES)
    days_allowed = models.PositiveIntegerField(default=0)
    carry_forward = models.BooleanField(default=False)
    requires_substitute = models.BooleanField(default=False)

    def __str__(self):
        return self.get_type_display()

class LeaveBalance(models.Model):
    employee = models.BigIntegerField()
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    last_updated = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.employee} - {self.leave_type} ({self.balance} days)"

class LeaveRequest(models.Model):
    employee = models.BigIntegerField()
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    purpose = models.TextField()
    substitute = models.BigIntegerField(null=True, blank=True)
    status = models.CharField(max_length=15, choices=[('PENDING', 'Pending'), ('APPROVED', 'Approved'), ('REJECTED', 'Rejected'), ('CANCELLED', 'Cancelled')])
    created_at = models.DateTimeField(default=timezone.now)
    approved_at = models.DateTimeField(null=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.employee} - {self.leave_type} ({self.start_date} - {self.end_date})"

class LeavePolicy(models.Model):
    type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    max_days = models.PositiveIntegerField(default=0)
    carry_forward = models.BooleanField(default=False)
    requires_substitute = models.BooleanField(default=False)
    holiday_calendar = models.BigIntegerField(null=True)

    def __str__(self):
        return f"{self.type} Policy"
