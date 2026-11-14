from django.db import models


class LeaveType(models.TextChoices):
    CL = 'CL', 'Casual Leave'
    RH = 'RH', 'Restricted Holiday'
    SCL = 'SCL', 'Special Casual Leave'
    EL = 'EL', 'Earned Leave'
    COL = 'COL', 'Compensatory Off'
    VL = 'VL', 'Vacation Leave'

class LeaveBalance(models.Model):
    employee_id = models.CharField(max_length=64)
    leave_type = models.CharField(max_length=4, choices=LeaveType.choices)
    balance = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('employee_id', 'leave_type')

    def __str__(self):
        return f'{self.employee_id}: {self.leave_type}'

class LeaveRequest(models.Model):
    employee_id = models.CharField(max_length=64)
    leave_type = models.CharField(max_length=4, choices=LeaveType.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=20, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.employee_id}: {self.start_date} to {self.end_date}'

    def duration(self):
        return (self.end_date - self.start_date).days + 1
