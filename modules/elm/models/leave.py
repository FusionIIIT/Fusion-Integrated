from decimal import Decimal
from django.db import models
from django.core.validators import MaxValueValidator
from core.db.mixins import TimeStampedModel, UserScopedModel


class LeaveCategory(models.TextChoices):
    CASUAL_LEAVE = 'CL', 'Casual Leave'
    RESTRICTED_HOLIDAY = 'RH', 'Restricted Holiday'
    SPECIAL_CASUAL_LEAVE = 'SCL', 'Special Casual Leave'
    EARNED_LEAVE = 'EL', 'Earned Leave'
    COMMUTED_LEAVE = 'COL', 'Commuted Leave'
    VACATION_LEAVE = 'VL', 'Vacation Leave'


class LeaveApplicationStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    AWAITING_SUBSTITUTE = 'AWAITING_SUBSTITUTE', 'Awaiting Substitute'
    APPLICANT_ACTION_REQUIRED = 'APPLICANT_ACTION_REQUIRED', 'Applicant Action Required'
    UNDER_REVIEW_UNIT_HEAD = 'UNDER_REVIEW_UNIT_HEAD', 'Under Review Unit Head'
    UNDER_REVIEW_ESTABLISHMENT = 'UNDER_REVIEW_ESTABLISHMENT', 'Under Review Establishment'
    UNDER_SANCTION = 'UNDER_SANCTION', 'Under Sanction'
    APPROVED = 'APPROVED', 'Approved'
    REJECTED = 'REJECTED', 'Rejected'
    WITHDRAWN = 'WITHDRAWN', 'Withdrawn'
    CANCELLED = 'CANCELLED', 'Cancelled'


class LeaveBalance(UserScopedModel, TimeStampedModel):
    year = models.IntegerField()
    leave_category = models.CharField(max_length=3, choices=LeaveCategory.choices)
    opening_balance = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.0'))
    credited = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.0'))
    availed = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.0'))
    pending_approval = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.0'))
    converted_from_vl = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.0'))
    lapsed = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.0'))
    carried_forward = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.0'))

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user_id', 'year', 'leave_category'], name='unique_leave_balance')
        ]

    def available_balance(self):
        return self.opening_balance + self.credited - self.availed - self.pending_approval - self.converted_from_vl - self.lapsed - self.carried_forward


class LeaveApplication(UserScopedModel, TimeStampedModel):
    leave_category = models.CharField(max_length=3, choices=LeaveCategory.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    half_day_type = models.CharField(max_length=11, choices=[('FIRST_HALF', 'First Half'), ('SECOND_HALF', 'Second Half')], null=True, blank=True)
    chargeable_days = models.DecimalField(max_digits=5, decimal_places=2, validators=[MaxValueValidator(60)])
    reason = models.TextField()
    status = models.CharField(max_length=32, choices=LeaveApplicationStatus.choices)
    has_station_leave = models.BooleanField(default=False)
    station_leave_destination = models.CharField(max_length=255, null=True, blank=True)
    station_leave_address = models.CharField(max_length=255, null=True, blank=True)
    station_leave_emergency_contact = models.CharField(max_length=255, null=True, blank=True)
    current_assigned_role = models.CharField(max_length=255, null=True, blank=True)
    current_assigned_user_id = models.IntegerField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)


class SubstituteAssignment(TimeStampedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    substitute_user_id = models.IntegerField()
    status = models.CharField(max_length=10, choices=[('PENDING', 'Pending'), ('ACCEPTED', 'Accepted'), ('DECLINED', 'Declined')])
    response_remarks = models.TextField(null=True, blank=True)
    responded_at = models.DateTimeField(null=True, blank=True)


class ApprovalHistory(TimeStampedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    actor_user_id = models.IntegerField()
    actor_role = models.CharField(max_length=255)
    action = models.CharField(max_length=20, choices=[('RECOMMENDED', 'Recommended'), ('NOT_RECOMMENDED', 'Not Recommended'), ('APPROVED', 'Approved'), ('REJECTED', 'Rejected'), ('WITHDRAWN', 'Withdrawn'), ('ESCALATED', 'Escalated')])
    remarks = models.TextField(null=True, blank=True)
    timestamp = models.DateTimeField()


class LeaveCancellation(TimeStampedModel):
    leave_application = models.OneToOneField(LeaveApplication, on_delete=models.CASCADE)
    applicant_user_id = models.IntegerField()
    reason = models.TextField()
    status = models.CharField(max_length=32, choices=[('PENDING_APPROVAL', 'Pending Approval'), ('APPROVED', 'Approved'), ('REJECTED', 'Rejected')])
    sanctioning_remarks = models.TextField(null=True, blank=True)


class LeaveExtension(TimeStampedModel):
    original_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    extended_end_date = models.DateField()
    additional_chargeable_days = models.DecimalField(max_digits=5, decimal_places=2)
    reason = models.TextField()
    substitute_required = models.BooleanField(default=False)
    status = models.CharField(max_length=10, choices=[('PENDING', 'Pending'), ('APPROVED', 'Approved'), ('REJECTED', 'Rejected')])


class LeaveResumption(TimeStampedModel):
    leave_application = models.OneToOneField(LeaveApplication, on_delete=models.CASCADE)
    actual_resumption_date = models.DateField()
    outcome = models.CharField(max_length=20, choices=[('NORMAL', 'Normal'), ('EARLY_SYNCHRONIZED', 'Early Synchronized'), ('LATE_SYNCHRONIZED', 'Late Synchronized')])
    status = models.CharField(max_length=15, choices=[('PENDING_REVIEW', 'Pending Review'), ('REVIEWED', 'Reviewed')])
    adjusted_days = models.DecimalField(max_digits=5, decimal_places=2)
    remarks = models.TextField(null=True, blank=True)


class OfflineLeaveRecord(TimeStampedModel):
    user_id = models.IntegerField()
    leave_category = models.CharField(max_length=3, choices=LeaveCategory.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    chargeable_days = models.DecimalField(max_digits=5, decimal_places=2)
    offline_sanction_reference = models.CharField(max_length=255)
    sanctioned_by_name = models.CharField(max_length=255)
    recorded_by_user_id = models.IntegerField()
    reason = models.TextField()


class SLAConfig(TimeStampedModel):
    task_type = models.CharField(max_length=255)
    reminder_hours = models.IntegerField()
    escalation_hours = models.IntegerField()
    escalation_target_role = models.CharField(max_length=255)