from django.db import models
from core.db.mixins import TimeStampedModel
from modules.directory.models import UserRef

class LeaveType(TimeStampedModel):
    code = models.CharField(primary_key=True, max_length=10)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    annual_quota = models.DecimalField(max_digits=5, decimal_places=1)
    is_vacation = models.BooleanField(default=False)
    max_continuous_days = models.IntegerField(default=30)

class LeaveBalance(TimeStampedModel):
    user = models.ForeignKey(UserRef, on_delete=models.CASCADE, related_name='leave_balances')
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    year = models.IntegerField()
    credited_days = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    used_days = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    balance = models.DecimalField(max_digits=5, decimal_places=1, default=0)
    class Meta:
        unique_together = ('user', 'leave_type', 'year')

class LeaveRequest(TimeStampedModel):
    applicant = models.ForeignKey(UserRef, on_delete=models.CASCADE, related_name='leave_requests')
    leave_type = models.ForeignKey(LeaveType, on_delete=models.PROTECT)
    start_date = models.DateField()
    end_date = models.DateField()
    half_day = models.BooleanField(default=False)
    half_day_period = models.CharField(max_length=15, choices=[('forenoon', 'Forenoon'), ('afternoon', 'Afternoon')], null=True, blank=True)
    purpose = models.TextField()
    station_leave = models.BooleanField(default=False)
    station_leave_address = models.TextField(blank=True)
    substitute = models.ForeignKey(UserRef, null=True, blank=True, on_delete=models.SET_NULL, related_name='substitute_requests')
    substitute_status = models.CharField(max_length=20, choices=[('pending', 'Pending'), ('accepted', 'Accepted'), ('declined', 'Declined')], default='pending')
    status = models.CharField(max_length=30, choices=[('draft', 'Draft'), ('awaiting_substitute', 'Awaiting Substitute Response'), ('pending_unit_head', 'Pending Unit Head Review'), ('pending_higher_sanction', 'Pending Higher Sanction'), ('approved', 'Approved'), ('rejected', 'Rejected'), ('withdrawn', 'Withdrawn'), ('cancelled', 'Cancelled')], default='pending_unit_head')

class LeaveActionLog(TimeStampedModel):
    leave_request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE, related_name='action_logs')
    actor = models.ForeignKey(UserRef, on_delete=models.CASCADE)
    role_name = models.CharField(max_length=50)
    action = models.CharField(max_length=30, choices=[('submitted', 'Submitted'), ('substitute_accepted', 'Substitute Accepted'), ('substitute_declined', 'Substitute Declined'), ('recommended', 'Recommended'), ('not_recommended', 'Not Recommended'), ('approved', 'Approved'), ('rejected', 'Rejected'), ('withdrawn', 'Withdrawn'), ('cancelled', 'Cancelled')])
    comments = models.TextField(blank=True)