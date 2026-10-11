from django.db import models
from django.contrib.auth.models import User

class LeaveType(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=10, unique=True)
    max_days_per_year = models.IntegerField()
    is_carry_forward = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class LeaveBalance(models.Model):
    user_id = models.IntegerField()  # Or ForeignKey to User model if preferred
    username = models.CharField(max_length=255)
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    year = models.IntegerField()
    balance = models.IntegerField(default=0)
    credited = models.IntegerField(default=0)
    utilized = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.username} - {self.leave_type.name}"

class LeaveApplication(models.Model):
    applicant_username = models.CharField(max_length=255)
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    half_day = models.BooleanField(default=False)
    status = models.CharField(
        max_length=20,
        choices=[
            ('PENDING', 'Pending'),
            ('APPROVED', 'Approved'),
            ('REJECTED', 'Rejected'),
            ('WITHDRAWN', 'Withdrawn'),
            ('CANCELLED', 'Cancelled'),
        ],
        default='PENDING'
    )
    reason = models.TextField(blank=True, null=True)
    substitute_username = models.CharField(max_length=255, blank=True, null=True)
    station_leave = models.TextField(blank=True, null=True)
    station_details = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Application by {self.applicant_username} for {self.leave_type.name}"

class LeaveAction(models.Model):
    application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE, related_name='actions')
    actor_username = models.CharField(max_length=255)
    action = models.CharField(
        max_length=20,
        choices=[
            ('RECOMMENDED', 'Recommended'),
            ('APPROVED', 'Approved'),
            ('REJECTED', 'Rejected'),
            ('COMMENTED', 'Commented'),
        ],
        default='RECOMMENDED'
    )
    remarks = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Action by {self.actor_username} on application {self.application.id}"