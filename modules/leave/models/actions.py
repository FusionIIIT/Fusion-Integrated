from django.db import models
from django.core.validators import MinValueValidator
from core.db.mixins import TimeStampedModel, UserScopedModel


class CancellationRequest(models.Model):
    """Models cancellation requests for pre-start leave (BR-EL-023)."""
    leave_request = models.ForeignKey(
        'leave.LeaveRequest',
        on_delete=models.CASCADE,
        related_name='cancellation_requests'
    )
    reason = models.TextField()
    status = models.CharField(
        max_length=50,
        choices=[
            ('pending_unit_head', 'Pending Unit Head'),
            ('pending_establishment', 'Pending Establishment'),
            ('pending_final', 'Pending Final Sanction'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
        ]
    )


class ExtensionRequest(models.Model):
    """Models extension requests for ongoing leave (BR-EL-025)."""
    leave_request = models.ForeignKey(
        'leave.LeaveRequest',
        on_delete=models.CASCADE,
        related_name='extension_requests'
    )
    requested_end_date = models.DateField()
    incremental_days = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(0.5)]
    )
    substitute_user_id = models.IntegerField(null=True, blank=True)
    status = models.CharField(
        max_length=50,
        choices=[
            ('awaiting_substitute', 'Awaiting Substitute'),
            ('applicant_action_required', 'Applicant Action Required'),
            ('awaiting_unit_head', 'Awaiting Unit Head'),
            ('pending_establishment', 'Pending Establishment'),
            ('pending_final', 'Pending Final Sanction'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
            ('withdrawn', 'Withdrawn'),
        ]
    )


class ResumptionRecord(models.Model):
    """Models resumption records (EL-UC-010, EL-UC-011, BR-EL-028)."""
    leave_request = models.ForeignKey(
        'leave.LeaveRequest',
        on_delete=models.CASCADE,
        related_name='resumption_records'
    )
    actual_resumption_date = models.DateField()
    diff_days = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(-14.0)]
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('normal', 'Normal'),
            ('early', 'Early'),
            ('late', 'Late'),
        ]
    )
    adjustment_applied = models.BooleanField(default=False)


class OfflineSanctionRecord(UserScopedModel):
    """Models offline-sanctioned leave records (BR-EL-029)."""
    category = models.CharField(
        max_length=10,
        choices=[
            ('cl', 'Casual Leave'),
            ('rh', 'Sick Leave'),
            ('scl', 'Special Casual Leave'),
            ('el', 'Earned Leave'),
            ('vl', 'Vacation Leave'),
            ('col', 'Compensatory Leave'),
        ]
    )
    start_date = models.DateField()
    end_date = models.DateField()
    chargeable_days = models.DecimalField(
        max_digits=6,
        decimal_places=2
    )
    sanction_order_ref = models.CharField(max_length=100)
    recorded_by_user_id = models.IntegerField()