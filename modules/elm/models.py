from django.db import models
from core.db.mixins import TimeStampedModel, UserScopedModel

class LeaveBalance(TimeStampedModel, UserScopedModel):
    category = models.CharField(max_length=10, choices=[('CL', 'Casual Leave'), ('RH', 'Recreational Holiday'), ('SCL', 'Sick Casual Leave'), ('EL', 'Earned Leave'), ('VL', 'Vacation Leave'), ('COL', 'Compensatory Off')])
    year = models.IntegerField()
    credited = models.DecimalField(max_digits=5, decimal_places=2)
    availed = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    balance = models.DecimalField(max_digits=5, decimal_places=2)

    class Meta:
        db_table = 'elm_leave_balance'
        constraints = [
            models.UniqueConstraint(fields=['user_id', 'category', 'year'], name='unique_leave_balance')
        ]

class LeaveRequest(TimeStampedModel, UserScopedModel):
    STATUS_CHOICES = [
        ('submitted', 'Submitted'),
        ('awaiting_substitute', 'Awaiting substitute consent'),
        ('under_review', 'Under Unit Head review'),
        ('recommended', 'Recommended to Sanctioning Authority'),
        ('sanctioned', 'Sanctioned'),
        ('rejected', 'Rejected'),
        ('withdrawn', 'Withdrawn'),
        ('cancelled', 'Cancelled'),
    ]
    category = models.CharField(max_length=10)
    start_date = models.DateField()
    end_date = models.DateField()
    half_day = models.CharField(max_length=10, blank=True, null=True, choices=[('first', 'First Half'), ('second', 'Second Half')])
    leave_days = models.DecimalField(max_digits=5, decimal_places=2)
    purpose = models.TextField()
    status = models.CharField(max_length=24, default='submitted')
    is_station_leave = models.BooleanField(default=False)
    destination = models.CharField(max_length=200, blank=True)
    emergency_contact = models.CharField(max_length=50, blank=True)
    substitute_id = models.IntegerField(null=True, blank=True)
    current_reviewer_id = models.IntegerField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    resumption_date = models.DateField(null=True, blank=True)
    resumption_status = models.CharField(max_length=20, default='none', choices=[('none', 'None'), ('pending', 'Pending Review'), ('completed', 'Completed')])
    is_offline_recorded = models.BooleanField(default=False)
    offline_reference = models.CharField(max_length=100, blank=True)

    class Meta:
        db_table = 'elm_leave_request'

class SubstituteAssignment(TimeStampedModel):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
    ]
    leave_request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE, related_name='substitute_assignments')
    substitute_id = models.IntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    remarks = models.TextField(blank=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'elm_substitute_assignment'

class LeaveActionHistory(TimeStampedModel):
    ACTION_CHOICES = [
        ('submitted', 'Submitted'),
        ('awaiting_substitute', 'Awaiting substitute consent'),
        ('under_review', 'Under Unit Head review'),
        ('recommended', 'Recommended to Sanctioning Authority'),
        ('sanctioned', 'Sanctioned'),
        ('rejected', 'Rejected'),
        ('withdrawn', 'Withdrawn'),
        ('cancelled', 'Cancelled'),
    ]
    leave_request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE, related_name='actions')
    actor_id = models.IntegerField()
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    comments = models.TextField(blank=True)

    class Meta:
        db_table = 'elm_leave_action_history'
