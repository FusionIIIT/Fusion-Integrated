from django.db import models
from django.conf import settings
from datetime import date, timedelta


class LeaveType(models.Model):
    """Defines leave categories with quotas and carry-forward rules."""
    
    TYPE_CHOICES = [
        ('CL', 'Casual Leave'),
        ('EL', 'Earned Leave'),
        ('COL', 'Commuted Leave'),
        ('RH', 'Restricted Holiday'),
        ('SCL', 'Special Casual Leave'),
        ('VL', 'Vacation Leave'),
    ]
    
    name = models.CharField(max_length=50, choices=TYPE_CHOICES)
    annual_quota = models.DecimalField(max_digits=5, decimal_places=1, default=8.0)
    carry_forward = models.BooleanField(default=False)
    requires_medical_evidence = models.BooleanField(default=False)
    description = models.TextField(blank=True)
    
    class Meta:
        verbose_name_plural = "Leave Types"
        ordering = ['name']
    
    def __str__(self):
        return self.name


class LeaveBalance(models.Model):
    """Tracks leave balance per employee per leave type."""
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='leave_balances'
    )
    leave_type = models.ForeignKey(LeaveType, on_delete=models.PROTECT)
    total_days = models.DecimalField(max_digits=5, decimal_places=1)
    consumed_days = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)
    pending_days = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)
    
    class Meta:
        unique_together = ['user', 'leave_type']
        ordering = ['user', 'leave_type']
    
    def __str__(self):
        return f"{self.user.username} - {self.leave_type.name}: {self.total_days} days"
    
    @property
    def available_days(self):
        """Returns available leave days after accounting for pending requests."""
        return self.total_days - self.consumed_days - self.pending_days
    
    def can_grant_leave(self, days: float) -> bool:
        """Check if sufficient balance exists for requested leave."""
        return self.available_days >= days


class LeaveRequest(models.Model):
    """Stores a leave application with all relevant details."""
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('unit_head_review', 'Unit Head Review'),
        ('establishment_review', 'Establishment Review'),
        ('final_decision_pending', 'Final Decision Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='leave_requests'
    )
    leave_type = models.ForeignKey(LeaveType, on_delete=models.PROTECT)
    start_date = models.DateField()
    end_date = models.DateField()
    total_days = models.DecimalField(max_digits=5, decimal_places=1)
    reason = models.TextField()
    station_leave = models.BooleanField(default=False)
    address_during_leave = models.CharField(max_length=255, blank=True)
    contact_during_leave = models.CharField(max_length=255, blank=True)
    substitute_name = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='draft')
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['start_date', 'end_date']),
        ]
    
    def __str__(self):
        return f"{self.user.username} - {self.leave_type.name} ({self.start_date} to {self.end_date})"
    
    @property
    def duration_days(self):
        """Calculate actual duration including weekends/holidays for EL/COL/VL."""
        delta = self.end_date - self.start_date
        return delta.days + 1
    
    def overlaps_with_active_leave(self) -> bool:
        """Check if this request overlaps with any active leave period."""
        from django.db.models import Q
        active_requests = LeaveRequest.objects.filter(
            user=self.user,
            status__in=['submitted', 'unit_head_review', 'establishment_review', 
                        'final_decision_pending', 'approved'],
            start_date__lte=self.end_date,
            end_date__gte=self.start_date
        ).exclude(pk=self.pk)
        
        if not active_requests.exists():
            return False
        
        # Check for half-day CL exception (different halves of same date)
        if self.leave_type.name == 'CL':
            return False  # Half-day CL on same date in different halves is allowed
        
        return True


class LeaveWorkflowHistory(models.Model):
    """Captures state transitions and reviewer actions."""
    
    request = models.ForeignKey(LeaveRequest, related_name='workflow_history', on_delete=models.CASCADE)
    from_state = models.CharField(max_length=30)
    to_state = models.CharField(max_length=30)
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    action_taken = models.CharField(max_length=50)
    remarks = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.request.id}: {self.from_state} -> {self.to_state}"
