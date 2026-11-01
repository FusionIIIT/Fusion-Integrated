"""Leave request models (BR-HR-007 to BR-HR-011)."""
from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel
from modules.hreis.domain.leave import LeaveStatus, LeaveType


class LeaveRequest(TimeStampedModel, UserScopedModel):
    """Leave application submitted by an employee."""

    user_id = models.IntegerField(db_index=True)
    leave_type = models.CharField(
        max_length=32,
        choices=[(t.value, t.name.title()) for t in LeaveType],
    )
    start_date = models.DateField()
    end_date = models.DateField()
    duration_days = models.DecimalField(max_digits=5, decimal_places=1)
    justification = models.TextField()
    status = models.CharField(
        max_length=32,
        choices=[(s.value, s.name.title()) for s in LeaveStatus],
        default=LeaveStatus.PENDING.value,
        db_index=True,
    )
    current_authority_role = models.CharField(max_length=64, default="hod", db_index=True)
    approval_history = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = "hreis_leave_request"
        verbose_name = "Leave Request"
        verbose_name_plural = "Leave Requests"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"LeaveRequest(id={self.id}, user={self.user_id}, type={self.leave_type}, status={self.status})"
