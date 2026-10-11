from django.db import models
from django.utils import timezone
from modules.placement.models.base import TimeStampedModel, UserScopedModel


class LeaveType(models.Model):
    """Supported leave types with their entitlement rules."""
    CODE = [
        ('CL', 'Casual Leave'),           # 0.5 half-day per month
        ('RH', 'Sick Leave'),             # Medical leave
        ('SCL', 'Special Casual Leave'),  # Special casual leave
        ('EL', 'Earned Leave'),           # Accumulated leave
        ('COL', 'Compensatory Leave'),    # Comp time for extra work
        ('VL', 'Voluntary Leave'),        # Voluntary unpaid leave
    ]
    
    code = models.CharField(max_length=10, choices=CODE, unique=True)
    name = models.CharField(max_length=50)
    entitlement_days_per_month = models.DecimalField(
        max_digits=3, decimal_places=2, default=0.5
    )
    is_renewable = models.BooleanField(default=True)
    
    class Meta:
        verbose_name_plural = 'Leave Types'
    
    def __str__(self):
        return f"{self.code}: {self.name}"


class LeaveRequest(TimeStampedModel, UserScopedModel):
    """A leave request submitted by an employee."""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]
    
    user = models.ForeignKey(
        'directory.UserRef',
        on_delete=models.CASCADE,
        related_name='leave_requests'
    )
    leave_type = models.ForeignKey(
        LeaveType,
        on_delete=models.PROTECT,
        related_name='requests'
    )
    category = models.CharField(max_length=50)  # CL, RH, SCL, EL, COL, VL
    half_day = models.BooleanField(default=False)
    start_date = models.DateField()
    end_date = models.DateField()
    station_address = models.CharField(max_length=255)
    station_details = models.TextField()
    substitute_employee = models.ForeignKey(
        'directory.UserRef',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='substituted_requests'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    approved_by = models.ForeignKey(
        'directory.UserRef',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_requests'
    )
    approval_date = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'start_date']),
        ]
    
    def __str__(self):
        return f"{self.user.name} - {self.category} ({self.start_date} to {self.end_date})"
    
    @property
    def duration_days(self) -> int:
        """Calculate total leave days (including half-days)."""
        delta = self.end_date - self.start_date
        full_days = delta.days + 1
        if self.half_day:
            return full_days * 0.5
        return full_days


class LeaveBalance(TimeStampedModel, UserScopedModel):
    """Tracks leave balance for a user."""
    user = models.ForeignKey(
        'directory.UserRef',
        on_delete=models.CASCADE,
        related_name='leave_balances'
    )
    leave_type = models.ForeignKey(
        LeaveType,
        on_delete=models.PROTECT,
        related_name='balances'
    )
    total_entitled = models.DecimalField(max_digits=6, decimal_places=2)
    used = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    available = models.DecimalField(max_digits=6, decimal_places=2)
    season_year = models.IntegerField()
    
    class Meta:
        unique_together = ['user', 'leave_type', 'season_year']
        ordering = ['-season_year']
    
    def __str__(self):
        return f"{self.user.name} - {self.leave_type.code} ({self.season_year})"
    
    @property
    def remaining(self) -> float:
        """Return available balance."""
        return self.available - self.used
