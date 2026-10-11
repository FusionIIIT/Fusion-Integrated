from django.db import models
from django.db.models import Q
from core.db.mixins import TimeStampedModel
from modules.elm.domain.state_machine import Status
from modules.elm.models.leave_types import LeaveType


class LeaveRequest(TimeStampedModel):
    employee_user_id = models.IntegerField(db_index=True)
    leave_type = models.ForeignKey(
        LeaveType, on_delete=models.PROTECT, related_name="requests"
    )
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField(max_length=2000)
    status = models.CharField(
        max_length=32,
        choices=[(status.value, status.value) for status in Status],
        default=Status.DRAFT.value,
        db_index=True,
    )

    class Meta:
        db_table = "elm_leave_request"
        constraints = [
            models.CheckConstraint(
                check=Q(start_date__lte=models.F("end_date")),
                name="valid_date_range",
            ),
        ]
        indexes = [
            models.Index(fields=["employee_user_id", "-created_at"], name="employee_history"),
            models.Index(fields=["status", "-created_at"], name="status_history"),
        ]

    def __str__(self):
        return f"Leave request for {self.employee_user_id} from {self.start_date} to {self.end_date}"


class LeaveRequestTransition(models.Model):
    leave_request = models.ForeignKey(
        LeaveRequest, on_delete=models.CASCADE, related_name="transitions"
    )
    from_status = models.CharField(
        max_length=32,
        choices=[(status.value, status.value) for status in Status],
    )
    to_status = models.CharField(
        max_length=32,
        choices=[(status.value, status.value) for status in Status],
    )
    actor_user_id = models.IntegerField(null=True, blank=True)
    reason = models.CharField(max_length=300, blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "elm_leave_request_transition"
        indexes = [models.Index(fields=["leave_request", "-at"], name="leave_request_desc_at")]
