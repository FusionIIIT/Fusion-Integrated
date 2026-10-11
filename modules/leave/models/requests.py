"""Leave request and audit trail models.

Implements core aggregate for leave applications and immutable audit trail.
"""
from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel
from modules.leave.domain.constants import (
    HalfDay,
    LeaveCategory,
    RequestStatus,
    SubstituteStatus,
    UnitHeadRecommendation,
)


class LeaveRequest(TimeStampedModel, UserScopedModel):
    category = models.CharField(max_length=10, choices=[(c.value, c.value) for c in LeaveCategory])
    start_date = models.DateField()
    end_date = models.DateField()
    half_day = models.CharField(
        max_length=20,
        choices=[(h.value, h.value) for h in HalfDay],
        default=HalfDay.NONE.value,
    )
    days_count = models.DecimalField(max_digits=5, decimal_places=1)
    purpose = models.TextField()

    # Station Leave coupling (BR-EL-013)
    station_leave_applied = models.BooleanField(default=False)
    station_details = models.JSONField(default=dict, blank=True)

    # State machine status
    status = models.CharField(
        max_length=50,
        choices=[(s.value, s.value) for s in RequestStatus],
        default=RequestStatus.DRAFT.value,
        db_index=True,
    )

    # Substitute gate (BR-EL-014, BR-EL-015)
    substitute_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    substitute_status = models.CharField(
        max_length=20,
        choices=[(s.value, s.value) for s in SubstituteStatus],
        default=SubstituteStatus.NOT_REQUIRED.value,
    )

    # Unit Head recommendation (BR-EL-017)
    unit_head_recommendation = models.CharField(
        max_length=20,
        choices=[(r.value, r.value) for r in UnitHeadRecommendation],
        default=UnitHeadRecommendation.NONE.value,
    )

    # Routing assignments
    current_assignee_role = models.CharField(max_length=50, blank=True)
    current_assignee_user_id = models.IntegerField(null=True, blank=True)
    department = models.CharField(max_length=100, blank=True)

    # Offline record synchronization (BR-EL-029)
    is_offline_record = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user_id", "status"]),
            models.Index(fields=["status", "department"]),
            models.Index(fields=["substitute_user_id", "substitute_status"]),
        ]


class LeaveAuditEvent(models.Model):
    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE, related_name="audit_events")
    event = models.CharField(max_length=50)
    from_state = models.CharField(max_length=50)
    to_state = models.CharField(max_length=50)
    actor_user_id = models.IntegerField()
    actor_role = models.CharField(max_length=50)
    remarks = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["timestamp"]
