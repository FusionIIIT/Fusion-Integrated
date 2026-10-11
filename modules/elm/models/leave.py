from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class LeaveTypeMaster(models.Model):
    TYPE_CHOICES = (
        ('CL', 'Casual Leave'),
        ('RH', 'Restricted Holiday'),
        ('SCL', 'Special Casual Leave'),
        ('EL', 'Earned Leave'),
        ('VL', 'Vacation Leave'),
        ('COL', 'Commuted Leave'),
    )
    code = models.CharField(max_length=5, choices=TYPE_CHOICES, unique=True)
    description = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"{self.code} - {self.get_code_display()}"


class LeaveStatusMaster(models.Model):
    STATUS_CHOICES = (
        ('DRAFT', 'Draft'),
        ('PENDING', 'Pending Recommendation'),
        ('RECOMMENDED', 'Recommended'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('CANCELLED', 'Cancelled'),
    )
    status_code = models.CharField(max_length=15, choices=STATUS_CHOICES, unique=True)

    def __str__(self):
        return self.status_code


class UserLeaveQuota(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='elm_quotas')
    academic_session = models.CharField(max_length=15, default='2025-2026')
    leave_type = models.ForeignKey(LeaveTypeMaster, on_delete=models.CASCADE)
    total_credited = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)
    total_availed = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)
    current_balance = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)

    class Meta:
        unique_together = ('user', 'academic_session', 'leave_type')


class LeaveApplication(models.Model):
    applicant = models.ForeignKey(User, on_delete=models.CASCADE, related_name='elm_requests')
    leave_type = models.ForeignKey(LeaveTypeMaster, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    number_of_days = models.DecimalField(max_digits=4, decimal_places=1, default=1.0)
    reason = models.TextField()
    status = models.ForeignKey(LeaveStatusMaster, on_delete=models.CASCADE)
    approving_authority = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='elm_supervised_requests')
    reviewer_comments = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.applicant.username} - {self.leave_type.code} ({self.start_date} to {self.end_date})"


class StationOutstationInfo(models.Model):
    application = models.OneToOneField(LeaveApplication, on_delete=models.CASCADE, related_name='outstation_detail')
    source_city = models.CharField(max_length=100, default='Jabalpur')
    target_destination = models.CharField(max_length=200)
    contact_number = models.CharField(max_length=25)
    residential_address = models.TextField()