from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class LeaveType(models.Model):
    """
    Leave categories defined under ELM synchronized baseline:
    CL, RH, SCL, EL, COL, VL.
    """
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
        return f"{self.code} - {self.name}"


class LeaveBalance(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='leave_balances')
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    balance = models.FloatField(default=0.0)
    year = models.IntegerField()

    class Meta:
        unique_together = ('user', 'leave_type', 'year')

    def __str__(self):
        return f"{self.user.username} - {self.leave_type.code}: {self.balance}"


class Leave(models.Model):
    """
    Main Leave Model.
    Status state machine supports substitute gating (BR-EL-015),
    Unit Head review (BR-EL-016/017), and withdrawal (BR-EL-022).
    """
    STATUS_CHOICES = [
        ('Awaiting_Substitute', 'Awaiting Substitute Response'),
        ('Action_Required', 'Applicant Action Required'),
        ('Awaiting_Unit_Head', 'Awaiting Unit Head Review'),
        ('Awaiting_Sanction', 'Awaiting Final Sanction'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
        ('Withdrawn', 'Withdrawn'),
        ('Cancellation_Pending', 'Cancellation Pending'),
        ('Cancelled', 'Cancelled'),
    ]
    HALF_DAY_CHOICES = [
        ('NONE', 'None'),
        ('FIRST', 'First Half'),
        ('SECOND', 'Second Half'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='leave_applications')
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    half_day = models.CharField(max_length=10, choices=HALF_DAY_CHOICES, default='NONE')
    reason = models.TextField()

    # Station Leave details integrated within same application (BR-EL-013)
    is_station_leave = models.BooleanField(default=False)
    station_leave_address = models.TextField(blank=True, null=True)

    # Substitute coverage (BR-EL-014 / BR-EL-015)
    substitute = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='substitute_requests'
    )
    substitute_accepted = models.BooleanField(default=False)

    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='Awaiting_Unit_Head')
    unit_head_recommendation = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} | {self.leave_type.code} ({self.start_date} to {self.end_date}) [{self.status}]"