from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class LeaveType(models.TextChoices):
    CASUAL = 'CL', 'Casual Leave'
    RESTRICTED_HOLIDAY = 'RH', 'Restricted Holiday'
    SPECIAL_CASUAL = 'SCL', 'Special Casual Leave'
    EARNED = 'EL', 'Earned Leave'
    VACATION = 'VL', 'Vacation Leave'
    COMMUTED = 'COL', 'Commuted Leave'

class LeaveStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    SUBMITTED = 'SUBMITTED', 'Submitted - Awaiting Unit Head'
    RECOMMENDED = 'RECOMMENDED', 'Recommended - Awaiting Higher Sanction'
    APPROVED = 'APPROVED', 'Approved'
    REJECTED = 'REJECTED', 'Rejected'
    CANCELLED = 'CANCELLED', 'Cancelled'

class LeaveBalance(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='elm_leave_balances')
    year = models.IntegerField(default=2026)
    leave_type = models.CharField(max_length=5, choices=LeaveType.choices)
    credited = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    consumed = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)
    available = models.DecimalField(max_digits=5, decimal_places=2, default=0.0)

    class Meta:
        unique_together = ('user', 'year', 'leave_type')

class EmployeeLeave(models.Model):
    applicant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='elm_leave_applications')
    leave_type = models.CharField(max_length=5, choices=LeaveType.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    duration_days = models.DecimalField(max_digits=4, decimal_places=1, default=1.0)
    is_half_day = models.BooleanField(default=False)
    half_day_slot = models.CharField(max_length=10, blank=True, null=True, choices=[('FIRST', 'First Half'), ('SECOND', 'Second Half')])
    purpose = models.TextField()
    status = models.CharField(max_length=15, choices=LeaveStatus.choices, default=LeaveStatus.SUBMITTED)
    applied_on = models.DateTimeField(auto_now_add=True)
    unit_head_remarks = models.TextField(blank=True, null=True)
    sanction_authority_remarks = models.TextField(blank=True, null=True)

    def __str__(self):
        return f'{self.applicant.username} - {self.leave_type} ({self.start_date} to {self.end_date})'

class StationLeaveDetail(models.Model):
    leave = models.OneToOneField(EmployeeLeave, on_delete=models.CASCADE, related_name='station_leave_detail')
    destination = models.CharField(max_length=255)
    departure_datetime = models.DateTimeField()
    return_datetime = models.DateTimeField()
    emergency_contact = models.CharField(max_length=20)
    address_during_leave = models.TextField()
