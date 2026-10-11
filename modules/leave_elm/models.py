from django.db import models

class LeaveApplication(models.Model):
    LEAVE_TYPES = [
        ('CL', 'Casual Leave'),
        ('RH', 'Regular Holiday'),
        ('SCL', 'Sick Leave'),
        ('EL', 'Earned Leave'),
        ('COL', 'Compensatory Off Leave'),
        ('VL', 'Variable Leave'),
    ]
    
    applicant_id = models.CharField(max_length=20)
    leave_type = models.CharField(max_length=5, choices=LEAVE_TYPES)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(max_length=20, default="pending")
    substitute_id = models.CharField(max_length=20, null=True, blank=True)
    station_leave = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
class LeaveBalance(models.Model):
    employee_id = models.CharField(max_length=20)
    leave_type = models.CharField(max_length=5)
    year = models.IntegerField()
    balance = models.DecimalField(max_digits=5, decimal_places=1)
    
class LeaveApprovalStep(models.Model):
    application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    approver_id = models.CharField(max_length=20)
    action = models.CharField(max_length=20)
    remarks = models.TextField(blank=True)
    acted_at = models.DateTimeField(auto_now_add=True)
