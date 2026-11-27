"""Leave request, substitution, and workflow transition models."""

from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel
from modules.leave.models.policy import LeaveType


class LeaveRequest(TimeStampedModel, UserScopedModel):
    """Core leave application row representing full lifecycle."""

    CADRE_CHOICES = [
        ("faculty", "Faculty"),
        ("staff", "Staff"),
    ]

    HALF_DAY_CHOICES = [
        ("first_half", "First Half"),
        ("second_half", "Second Half"),
    ]

    RECONCILIATION_STATUS = [
        ("none", "None"),
        ("pending_admin_policy", "Pending Admin Policy"),
        ("synchronized", "Synchronized"),
    ]

    UNIT_HEAD_RECOMMENDATION_CHOICES = [
        ("recommended", "Recommended"),
        ("not_recommended", "Not Recommended"),
    ]

    application_number = models.CharField(max_length=32, unique=True)
    cadre = models.CharField(max_length=20, choices=CADRE_CHOICES)
    department = models.CharField(
        max_length=80, blank=True, db_index=True
    )  # Server-side directory snapshot
    leave_type = models.ForeignKey(LeaveType, on_delete=models.PROTECT, related_name="requests")
    start_date = models.DateField()
    end_date = models.DateField()
    is_half_day = models.BooleanField(default=False)
    half_day_period = models.CharField(max_length=15, blank=True, choices=HALF_DAY_CHOICES)
    requested_days = models.DecimalField(max_digits=5, decimal_places=1)
    reason = models.TextField()
    address_during_leave = models.TextField(blank=True)
    contact_number = models.CharField(max_length=30, blank=True)

    # Station Leave Coupling (BR-EL-013, Problem Statement ?2)
    is_station_leave = models.BooleanField(default=False)
    station_departure_date = models.DateField(null=True, blank=True)
    station_arrival_date = models.DateField(null=True, blank=True)
    station_destination = models.CharField(max_length=150, blank=True)

    # Authoritative workflow state from LeaveState
    status = models.CharField(max_length=50, default="draft", db_index=True)
    current_handler_role = models.CharField(max_length=50, blank=True)
    current_handler_user_id = models.IntegerField(null=True, blank=True)

    # Unit Head Review & Recommendation (BR-EL-017, EL-UC-003)
    unit_head_recommendation = models.CharField(
        max_length=20, blank=True, choices=UNIT_HEAD_RECOMMENDATION_CHOICES
    )
    unit_head_remarks = models.TextField(blank=True)

    # Approved Leave Cancellation (BR-EL-023, CW-EL-02, EL-UC-008)
    cancellation_reason = models.TextField(blank=True)
    cancellation_requested_at = models.DateTimeField(null=True, blank=True)

    # Ongoing Leave Extension (BR-EL-025, CW-EL-03, EL-UC-009)
    extension_end_date = models.DateField(null=True, blank=True)
    extension_days = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    extension_reason = models.TextField(blank=True)

    # Deficit Governance & Late-Resumption reconciliation (BR-EL-028, DEC-ELM-001)
    requires_admin_review = models.BooleanField(default=False)
    reconciliation_status = models.CharField(
        max_length=30, default="none", choices=RECONCILIATION_STATUS
    )
    actual_days = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    excess_days = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)

    # Offline Sanctioned Leave (BR-EL-029)
    is_offline_record = models.BooleanField(default=False)
    offline_sanction_reference = models.CharField(max_length=100, blank=True)
    offline_sanctioned_by = models.CharField(max_length=100, blank=True)
    offline_sanctioned_date = models.DateField(null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.application_number} ({self.status}) - User {self.user_id}"


class SubstituteNomination(TimeStampedModel):
    """Substitute responsibility coverage and consent gate (BR-EL-014..015)."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("declined", "Declined"),
    ]

    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE, related_name="substitutes")
    substitute_user_id = models.IntegerField(db_index=True)
    status = models.CharField(max_length=20, default="pending", choices=STATUS_CHOICES)
    remarks = models.TextField(blank=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    sequence = models.PositiveSmallIntegerField(default=1)  # 1 for first nominee, 2 for replacement

    def __str__(self) -> str:
        return f"{self.request.application_number}: Sub {self.substitute_user_id} ({self.status})"


class WorkflowTransition(TimeStampedModel):
    """Immutable audit trail of state transitions across all workflows."""

    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE, related_name="transitions")
    from_state = models.CharField(max_length=50)
    to_state = models.CharField(max_length=50)
    action = models.CharField(max_length=50)
    actor_user_id = models.IntegerField()
    actor_role = models.CharField(max_length=50)
    remarks = models.TextField(blank=True)

    def __str__(self) -> str:
        return (
            f"{self.request.application_number}: "
            f"{self.from_state} -> {self.to_state} by {self.actor_role}"
        )
