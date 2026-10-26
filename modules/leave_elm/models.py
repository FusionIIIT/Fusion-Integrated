from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User


class LeaveType(models.Model):
    """
    ELM Supported Leave Categories (BR-EL-001):
    CL (Casual Leave), RH (Restricted Holiday), SCL (Special Casual Leave),
    EL (Earned Leave), COL (Commuted / Medical Leave), VL (Vacation Leave).
    """
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, unique=True)
    max_days_per_year = models.DecimalField(max_digits=5, decimal_places=2)
    is_carry_forward = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    requires_vacation_period = models.BooleanField(default=False)  # BR-EL-006 (VL)
    requires_medical_evidence = models.BooleanField(default=False)  # BR-EL-009 (COL)

    def __str__(self):
        return f"{self.code} - {self.name}"


class LeaveBalance(models.Model):
    """
    Tracks annual credited, utilized, and remaining leave balances per employee (BR-EL-002 to BR-EL-009).
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    username = models.CharField(max_length=150, db_index=True)
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    year = models.IntegerField(db_index=True)
    balance = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.0'))
    credited = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.0'))
    utilized = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('0.0'))

    class Meta:
        unique_together = ('username', 'leave_type', 'year')

    def __str__(self):
        return f"{self.username} - {self.leave_type.code} ({self.year}): {self.balance}"


class LeaveApplication(models.Model):
    """
    Core Leave Application entity supporting full lifecycle state transitions (BR-EL-010 to BR-EL-028).
    """
    STATUS_CHOICES = [
        ('SUBSTITUTE_PENDING', 'Pending Substitute Consent'),
        ('PENDING_UNIT_HEAD', 'Pending Unit Head Approval'),
        ('PENDING_HIGHER_SANCTION', 'Pending Higher Sanction'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('WITHDRAWN', 'Withdrawn'),
        ('CANCELLED', 'Cancelled'),
    ]

    HALF_DAY_CHOICES = [
        ('NONE', 'Full Day'),
        ('FIRST_HALF', 'First Half'),
        ('SECOND_HALF', 'Second Half'),
    ]

    SUBSTITUTE_STATUS_CHOICES = [
        ('NOT_REQUIRED', 'Not Required'),
        ('PENDING', 'Pending Consent'),
        ('ACCEPTED', 'Accepted'),
        ('DECLINED', 'Declined'),
    ]

    RECOMMENDATION_CHOICES = [
        ('NONE', 'None'),
        ('RECOMMENDED', 'Recommended'),
        ('NOT_RECOMMENDED', 'Not Recommended'),
    ]

    applicant_username = models.CharField(max_length=150, db_index=True)
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    half_day = models.BooleanField(default=False)
    half_day_period = models.CharField(max_length=20, choices=HALF_DAY_CHOICES, default='NONE')
    days_count = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.0'))
    
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='PENDING_UNIT_HEAD')
    reason = models.TextField(blank=True)
    
    # Substitute Workflow (BR-EL-014, BR-EL-015)
    substitute_username = models.CharField(max_length=150, blank=True, null=True)
    substitute_status = models.CharField(max_length=20, choices=SUBSTITUTE_STATUS_CHOICES, default='NOT_REQUIRED')
    substitute_remarks = models.TextField(blank=True, null=True)

    # Station Leave Coupling (BR-EL-013)
    station_leave = models.BooleanField(default=False)
    station_details = models.JSONField(null=True, blank=True)

    # Routing and Authority (BR-EL-016, BR-EL-017, BR-EL-018)
    unit_head_recommendation = models.CharField(max_length=20, choices=RECOMMENDATION_CHOICES, default='NONE')
    unit_head_remarks = models.TextField(blank=True, null=True)
    higher_sanction_authority = models.CharField(max_length=100, blank=True, null=True)
    sanction_remarks = models.TextField(blank=True, null=True)

    # Resumption & Lifecycle (BR-EL-023, BR-EL-025, BR-EL-027, BR-EL-028)
    actual_resumption_date = models.DateField(null=True, blank=True)
    cancellation_reason = models.TextField(blank=True, null=True)
    is_extension = models.BooleanField(default=False)
    original_application = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"App #{self.pk}: {self.applicant_username} - {self.leave_type.code} ({self.status})"


class LeaveAction(models.Model):
    """
    Immutable audit trail of actions taken on an application.
    """
    ACTION_CHOICES = [
        ('SUBMITTED', 'Submitted'),
        ('SUBSTITUTE_ACCEPTED', 'Substitute Accepted'),
        ('SUBSTITUTE_DECLINED', 'Substitute Declined'),
        ('RECOMMENDED', 'Recommended by Unit Head'),
        ('NOT_RECOMMENDED', 'Not Recommended by Unit Head'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('WITHDRAWN', 'Withdrawn'),
        ('CANCELLED', 'Cancelled'),
        ('RESUMPTION_RECORDED', 'Resumption Recorded'),
        ('COMMENTED', 'Commented'),
    ]

    application = models.ForeignKey(LeaveApplication, related_name='actions', on_delete=models.CASCADE)
    actor_username = models.CharField(max_length=150)
    action = models.CharField(max_length=30, choices=ACTION_CHOICES)
    remarks = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Action #{self.pk} by {self.actor_username}: {self.action} on App #{self.application_id}"


class HolidayCalendar(models.Model):
    """
    Published Holiday / Restricted Holiday Calendar (BR-EL-003, BR-EL-031).
    """
    date = models.DateField(unique=True)
    name = models.CharField(max_length=150)
    is_restricted_holiday = models.BooleanField(default=False)  # True for RH, False for Closed Holiday
    year = models.IntegerField(db_index=True)

    def __str__(self):
        type_str = "RH" if self.is_restricted_holiday else "Closed"
        return f"{self.date} ({type_str}): {self.name}"