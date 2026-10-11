from django.db import models
from django.contrib.auth.models import User

class LeaveType(models.Model):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, unique=True)
    max_days_per_year = models.IntegerField()
    is_carry_forward = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class LeaveBalance(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    year = models.IntegerField()
    balance = models.DecimalField(max_digits=5, decimal_places=2)
    credited = models.DecimalField(max_digits=5, decimal_places=2)
    utilized = models.DecimalField(max_digits=5, decimal_places=2)

    def __str__(self):
        return f"{self.user.username} - {self.leave_type.name}"

class LeaveApplication(models.Model):
    applicant_username = models.CharField(max_length=100)
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    half_day = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=[
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('WITHDRAWN', 'Withdrawn'),
        ('CANCELLED', 'Cancelled')
    ])
    reason = models.TextField(blank=True)
    substitute_username = models.CharField(max_length=100, blank=True)
    station_leave = models.BooleanField(default=False)
    station_details = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.applicant_username} - {self.leave_type.name}"

class LeaveAction(models.Model):
    application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    actor_username = models.CharField(max_length=100)
    action = models.CharField(max_length=20, choices=[
        ('RECOMMENDED', 'Recommended'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('COMMENTED', 'Commented')
    ])
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.actor_username} - {self.action}"