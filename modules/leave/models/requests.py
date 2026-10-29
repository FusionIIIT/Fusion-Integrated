"""
Leave Request Models - Core leave application and workflow tracking.

STAGE 2: DATABASE MODELS & MIGRATIONS, Item 3
"""

from django.db import models
from django.core.validators import MinValueValidator

from core.db.mixins import TimeStampedModel, UserScopedModel

# Import status constants from domain
from modules.leave.domain.constants import (
    DRAFT, AWAITING_SUBSTITUTE, APPLICANT_ACTION_REQUIRED, AWAITING_UNIT_HEAD,
    AWAITING_ESTABLISHMENT, AWAITING_FINAL_SANCTION, AWAITING_DIRECTOR_SANCTION,
    APPROVED, REJECTED, WITHDRAWN, CANCELLED, CANCELLATION_REJECTED,
    EXTENSION_AWAITING_SUBSTITUTE, EXTENSION_APPLICANT_ACTION_REQUIRED,
    EXTENSION_AWAITING_UNIT_HEAD, EXTENSION_PENDING_ESTABLISHMENT,
    EXTENSION_PENDING_FINAL, EXTENSION_APPROVED, EXTENSION_REJECTED,
    EXTENSION_WITHDRAWN, RESUMPTION_PENDING, RESUMPTION_NORMAL,
    RESUMPTION_EARLY, RESUMPTION_LATE, SUBSTITUTE_NONE,
    SUBSTITUTE_PENDING, SUBSTITUTE_ACCEPTED, SUBSTITUTE_DECLINED,
    HALF_DAY_NONE, HALF_DAY_FIRST, HALF_DAY_SECOND,
    EMPLOYEE, SUBSTITUTE, UNIT_HEAD, ESTABLISHMENT,
    SANCTIONING_AUTHORITY, DIRECTOR, LEAVE_ADMIN, SYSTEM,
)


class LeaveRequest(UserScopedModel, TimeStampedModel):
    """
    Core leave request model with full workflow state tracking.
    """
    
    category = models.CharField(max_length=10, choices=[
        ('cl', 'Casual Leave'),
        ('rh', 'Half Leave'),
        ('scl', 'Sick Leave'),
        ('el', 'Earned Leave'),
        ('vl', 'Vacation Leave'),
        ('col', 'Compensatory Leave'),
    ])
    start_date = models.DateField()
    end_date = models.DateField()
    half_day_type = models.CharField(max_length=15, choices=[
        (HALF_DAY_NONE, 'none'),
        (HALF_DAY_FIRST, 'first_half'),
        (HALF_DAY_SECOND, 'second_half'),
    ], default=HALF_DAY_NONE)
    chargeable_days = models.DecimalField(max_digits=5, decimal_places=2, default=0.00,
                                          validators=[MinValueValidator(0.0)])
    purpose = models.TextField()
    station_leave_required = models.BooleanField(default=False)
    station_leave_details = models.JSONField(blank=True, null=True)
    substitute_user_id = models.IntegerField(null=True, blank=True)
    substitute_status = models.CharField(max_length=15, choices=[
        (SUBSTITUTE_NONE, SUBSTITUTE_NONE),
        (SUBSTITUTE_PENDING, SUBSTITUTE_PENDING),
        (SUBSTITUTE_ACCEPTED, SUBSTITUTE_ACCEPTED),
        (SUBSTITUTE_DECLINED, SUBSTITUTE_DECLINED),
    ], default=SUBSTITUTE_NONE)
    status = models.CharField(max_length=50, choices=[
        (DRAFT, DRAFT),
        (AWAITING_SUBSTITUTE, AWAITING_SUBSTITUTE),
        (APPLICANT_ACTION_REQUIRED, APPLICANT_ACTION_REQUIRED),
        (AWAITING_UNIT_HEAD, AWAITING_UNIT_HEAD),
        (AWAITING_ESTABLISHMENT, AWAITING_ESTABLISHMENT),
        (AWAITING_FINAL_SANCTION, AWAITING_FINAL_SANCTION),
        (AWAITING_DIRECTOR_SANCTION, AWAITING_DIRECTOR_SANCTION),
        (APPROVED, APPROVED),
        (REJECTED, REJECTED),
        (WITHDRAWN, WITHDRAWN),
        (CANCELLED, CANCELLED),
        (CANCELLATION_REJECTED, CANCELLATION_REJECTED),
        (EXTENSION_AWAITING_SUBSTITUTE, EXTENSION_AWAITING_SUBSTITUTE),
        (EXTENSION_APPLICANT_ACTION_REQUIRED, EXTENSION_APPLICANT_ACTION_REQUIRED),
        (EXTENSION_AWAITING_UNIT_HEAD, EXTENSION_AWAITING_UNIT_HEAD),
        (EXTENSION_PENDING_ESTABLISHMENT, EXTENSION_PENDING_ESTABLISHMENT),
        (EXTENSION_PENDING_FINAL, EXTENSION_PENDING_FINAL),
        (EXTENSION_APPROVED, EXTENSION_APPROVED),
        (EXTENSION_REJECTED, EXTENSION_REJECTED),
        (EXTENSION_WITHDRAWN, EXTENSION_WITHDRAWN),
        (RESUMPTION_PENDING, RESUMPTION_PENDING),
        (RESUMPTION_NORMAL, RESUMPTION_NORMAL),
        (RESUMPTION_EARLY, RESUMPTION_EARLY),
        (RESUMPTION_LATE, RESUMPTION_LATE),
    ], default=DRAFT)
    is_faculty = models.BooleanField(default=False)
    current_assignee_id = models.IntegerField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user_id', 'category', 'status']),
            models.Index(fields=['user_id', 'start_date', 'end_date']),
        ]
    
    def __str__(self):
        return f"{self.user_id} - {self.category} - {self.start_date} to {self.end_date} ({self.status})"


class LeaveRequestTransition(UserScopedModel, TimeStampedModel):
    """
    Audit trail for all state changes in leave requests.
    """
    
    leave_request = models.ForeignKey('LeaveRequest', on_delete=models.CASCADE, related_name='transitions')
    from_status = models.CharField(max_length=50)
    to_status = models.CharField(max_length=50)
    actor_user_id = models.IntegerField()
    actor_role = models.CharField(max_length=50, choices=[
        (EMPLOYEE, EMPLOYEE),
        (SUBSTITUTE, SUBSTITUTE),
        (UNIT_HEAD, UNIT_HEAD),
        (ESTABLISHMENT, ESTABLISHMENT),
        (SANCTIONING_AUTHORITY, SANCTIONING_AUTHORITY),
        (DIRECTOR, DIRECTOR),
        (LEAVE_ADMIN, LEAVE_ADMIN),
        (SYSTEM, SYSTEM),
    ])
    remarks = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['leave_request', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.leave_request_id} - {self.from_status} -> {self.to_status} by {self.actor_role}"
