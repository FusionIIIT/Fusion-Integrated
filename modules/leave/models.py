from django.db import models
from django.utils import timezone
import decimal

class LeaveType(models.TextChoices):
    CL = 'CL', 'Casual Leave'
    RH = 'RH', 'Restricted Holiday'
    SCL = 'SCL', 'Special Casual Leave'
    EL = 'EL', 'Earned Leave'
    COL = 'COL', 'Commuted Leave'
    VL = 'VL', 'Vacation Leave'

class LeaveDayPeriod(models.TextChoices):
    FULL_DAY = 'full_day', 'Full Day'
    FIRST_HALF = 'first_half', 'First Half'
    SECOND_HALF = 'second_half', 'Second Half'

class LeaveStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    APPROVED = 'approved', 'Approved'
    REJECTED = 'rejected', 'Rejected'
    WITHDRAWN = 'withdrawn', 'Withdrawn'
    CANCELLED = 'cancelled', 'Cancelled'

class LeaveBalance(models.Model):
    employee_id = models.CharField(max_length=64)
    leave_type = models.CharField(max_length=4, choices=LeaveType.choices)
    balance = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('employee_id', 'leave_type')

class LeaveRequest(models.Model):
    employee_id = models.CharField(max_length=64)
    leave_type = models.CharField(max_length=4, choices=LeaveType.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=LeaveStatus.choices, default=LeaveStatus.PENDING)
    day_period = models.CharField(
        max_length=12,
        choices=LeaveDayPeriod.choices,
        default=LeaveDayPeriod.FULL_DAY,
    )
    is_station_leave = models.BooleanField(default=False)
    station_address = models.CharField(max_length=255, blank=True, default='')
    station_contact = models.CharField(max_length=32, blank=True, default='')
    substitute_id = models.CharField(max_length=64, blank=True, default='')
    rejection_reason = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def duration(self):
        if self.day_period in (LeaveDayPeriod.FIRST_HALF, LeaveDayPeriod.SECOND_HALF):
            return decimal.Decimal('0.5')
        # Full day: inclusive calendar-day count
        days = (self.end_date - self.start_date).days + 1
        return decimal.Decimal(days)
