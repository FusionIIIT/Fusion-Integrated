from django.db import models
from fusion_auth.models import UserRef, Principal

class LeaveType(models.Model):
    CODE_CHOICES = [
        ('CL', 'Casual Leave'),
        ('RH', 'Restricted Holiday'),
        ('SCL', 'Special Casual Leave'),
        ('EL', 'Earned Leave'),
        ('COL', 'Commuted Leave'),
        ('VL', 'Vacation Leave'),
    ]
    code = models.CharField(max_length=10, choices=CODE_CHOICES, unique=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

class LeaveBalance(models.Model):
    user = models.ForeignKey(UserRef, on_delete=models.CASCADE)
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    balance = models.FloatField(default=0.0)
    year = models.IntegerField()

    class Meta:
        unique_together = ('user', 'leave_type', 'year')

    def __str__(self):
        return f"{self.user} - {self.leave_type.code}: {self.balance}"

class Leave(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
        ('Cancelled', 'Cancelled'),
        ('Withdrawn', 'Withdrawn'),
    ]
    HALF_DAY_CHOICES = [
        ('NONE', 'None'),
        ('FIRST', 'First Half'),
        ('SECOND', 'Second Half'),
    ]

    user = models.ForeignKey(UserRef, on_delete=models.CASCADE, related_name='leave_applications')
    principal = models.ForeignKey(Principal, on_delete=models.CASCADE, null=True, blank=True)
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    half_day = models.CharField(max_length=10, choices=HALF_DAY_CHOICES, default='NONE')
    reason = models.TextField()
    
    # Station Leave integration
    is_station_leave = models.BooleanField(default=False)
    station_leave_address = models.TextField(blank=True, null=True)
    
    # Substitute / Responsibility Coverage
    substitute = models.ForeignKey(UserRef, on_delete=models.SET_NULL, null=True, blank=True, related_name='substitute_leaves')
    substitute_accepted = models.BooleanField(default=False)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.leave_type.code} ({self.start_date} to {self.end_date}) [{self.status}]"