"""Leave requests and append-only request transition history."""

from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel, UserScopedModel


class LeaveRequest(TimeStampedModel, UserScopedModel):
    LEAVE_TYPES = [
        ("CL", "Casual Leave"),
        ("RH", "Restricted Holiday"),
        ("SCL", "Special Casual Leave"),
        ("EL", "Earned Leave"),
        ("COL", "Compensatory Leave"),
        ("VL", "Vacation Leave"),
    ]

    STATUSES = [
        ("draft", "Draft"),
        ("submitted", "Submitted"),
        ("pending", "Pending Approval"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("withdrawn", "Withdrawn"),
        ("cancelled", "Cancelled"),
    ]

    leave_type = models.CharField(max_length=3, choices=LEAVE_TYPES)
    start_date = models.DateField()
    end_date = models.DateField()
    half_day = models.CharField(
        max_length=6,
        choices=[("first", "First Half"), ("second", "Second Half")],
        blank=True,
        default="",
    )
    reason = models.TextField(blank=True)
    status = models.CharField(
        max_length=12,
        choices=STATUSES,
        default="draft",
        db_index=True,
    )
    submitted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "elm_leave_request"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(end_date__gte=models.F("start_date")),
                name="elm_leave_dates_valid",
            ),
            models.CheckConstraint(
                condition=(
                    Q(half_day__isnull=True)
                    | (
                        Q(leave_type="CL")
                        & Q(start_date=models.F("end_date"))
                    )
                ),
                name="elm_half_day_cl_only",
            ),
        ]
        indexes = [
            models.Index(
                fields=["user_id", "status"],
                name="elm_request_user_status",
            ),
            models.Index(
                fields=["start_date", "end_date"],
                name="elm_request_dates",
            ),
        ]

    def __str__(self):
        return f"ELM request #{self.pk} by user {self.user_id}"


class LeaveRequestTransition(models.Model):
    """Append-only record of each request status transition."""

    leave_request = models.ForeignKey(
        LeaveRequest,
        on_delete=models.PROTECT,
        related_name="transitions",
    )
    from_status = models.CharField(max_length=12, blank=True)
    to_status = models.CharField(max_length=12)
    actor_user_id = models.IntegerField(null=True, blank=True)
    actor_label = models.CharField(max_length=80, blank=True)
    reason = models.CharField(max_length=500, blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "elm_leave_request_transition"
        ordering = ["at"]
        indexes = [
            models.Index(
                fields=["leave_request", "at"],
                name="elm_transition_req_at",
            ),
        ]

    def __str__(self):
        return (
            f"request #{self.leave_request_id}: "
            f"{self.from_status}->{self.to_status}"
        )
