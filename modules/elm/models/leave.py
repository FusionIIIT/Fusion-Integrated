from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from decimal import Decimal

class LeaveCategory(models.TextChoices):
    CL = 'CL', 'Casual Leave'
    RH = 'RH', 'Restricted Holiday'
    SCL = 'SCL', 'Special Casual Leave'
    EL = 'EL', 'Earned Leave'
    COL = 'COL', 'Commuted Leave'
    VL = 'VL', 'Vacation Leave'

class PartOfDay(models.TextChoices):
    FULL = 'full', 1.0
    FIRST_HALF = 'first_half', 0.5
    SECOND_HALF = 'second_half', 0.5

class LeaveStatus(models.TextChoices):
    SUBMITTED = 'submitted'
    PENDING_SUBSTITUTE = 'pending_substitute'
    SUBSTITUTE_DECLINED = 'substitute_declined'
    PENDING_UNIT_HEAD = 'pending_unit_head'
    RECOMMENDED = 'recommended'
    NOT_RECOMMENDED = 'not_recommended'
    PENDING_SANCTION = 'pending_sanction'
    APPROVED = 'approved'
    REJECTED = 'rejected'
    WITHDRAWN = 'withdrawn'
    CANCELLATION_REQUESTED = 'cancellation_requested'
    CANCELLED = 'cancelled'
    CANCELLATION_REJECTED = 'cancellation_rejected'
    EXTENSION_REQUESTED = 'extension_requested'
    RESUMPTION_REQUESTED = 'resumption_requested'

class LeaveRequest(models.Model):
    user_id = models.PositiveBigIntegerField(db_index=True)
    category = models.CharField(max_length=3, choices=LeaveCategory.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    part_of_day = models.CharField(max_length=10, choices=PartOfDay.choices, default=PartOfDay.FULL)
    computed_days = models.DecimalField(max_digits=6, decimal_places=2, default=1.0)
    reason = models.TextField()
    station_leave = models.BooleanField(default=False)
    station_destination = models.CharField(max_length=255, blank=True)
    substitute_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    substitute_status = models.CharField(max_length=10, default='none')  # none, pending, accepted, declined
    status = models.CharField(max_length=32, choices=LeaveStatus.choices, default=LeaveStatus.SUBMITTED)
    unit_head_recommendation = models.CharField(max_length=20, blank=True)  # pending, recommended, not_recommended, approved, rejected
    unit_head_note = models.TextField(blank=True)
    final_decision = models.CharField(max_length=20, blank=True)  # approved, rejected
    final_decision_note = models.TextField(blank=True)
    final_decision_by = models.PositiveBigIntegerField(null=True, blank=True)
    decision_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class LeaveBalance(models.Model):
    user_id = models.PositiveBigIntegerField(db_index=True)
    year = models.PositiveSmallIntegerField()
    category = models.CharField(max_length=3, choices=LeaveCategory.choices)
    entitled_days = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    used_days = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    pending_days = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    
    @property
    def available_days(self):
        return max(Decimal('0'), self.entitled_days - self.used_days - self.pending_days)
        
    class Meta:
        constraints = [models.UniqueConstraint(fields=['user_id', 'year', 'category'], name='unique_balance')]

class LeaveSubstituteConsent(models.Model):
    request = models.ForeignKey(LeaveRequest, related_name='substitute_consents', on_delete=models.CASCADE)
    substitute_user_id = models.PositiveBigIntegerField()
    status = models.CharField(max_length=10, choices=[('pending', 'Pending'), ('accepted', 'Accepted'), ('declined', 'Declined')])
    response_note = models.TextField(blank=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    is_current = models.BooleanField(default=True)

class DutyResumption(models.Model):
    request = models.OneToOneField(LeaveRequest, related_name='resumption', on_delete=models.CASCADE)
    actual_resumption_date = models.DateField()
    resumption_type = models.CharField(max_length=10, choices=[('normal', 'Normal'), ('early', 'Early'), ('late', 'Late')])
    adjustment_days = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    reason = models.TextField(blank=True)
    reviewed_by = models.PositiveBigIntegerField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=[('submitted', 'Submitted'), ('approved', 'Approved'), ('rejected', 'Rejected')])
    created_at = models.DateTimeField(auto_now_add=True)

class LeaveExtension(models.Model):
    original_request = models.ForeignKey(LeaveRequest, related_name='extensions', on_delete=models.CASCADE)
    extension_start_date = models.DateField()
    extension_end_date = models.DateField()
    additional_days = models.DecimalField(max_digits=6, decimal_places=2)
    reason = models.TextField()
    substitute_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    status = models.CharField(max_length=32, choices=LeaveStatus.choices)
    created_at = models.DateTimeField(auto_now_add=True)

class HolidayCalendar(models.Model):
    date = models.DateField(unique=True)
    name = models.CharField(max_length=150)
    is_rh = models.BooleanField(default=False)
    year = models.PositiveSmallIntegerField()

class LeavePolicy(models.Model):
    category = models.CharField(max_length=3, choices=LeaveCategory.choices, unique=True)
    annual_entitlement = models.DecimalField(max_digits=6, decimal_places=2)
    is_continuous_counting = models.BooleanField(default=False)  # True for EL, COL, VL
    carries_forward = models.BooleanField(default=False)  # True for EL, COL
    allows_half_day = models.BooleanField(default=False)  # True for CL
    vl_to_el_conversion_ratio = models.DecimalField(max_digits=4, decimal_places=2, default=0.50)  # 2 VL : 1 EL

class LeaveAction(models.Model):
    request = models.ForeignKey(LeaveRequest, related_name='actions', on_delete=models.CASCADE)
    actor_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    action = models.CharField(max_length=32)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
