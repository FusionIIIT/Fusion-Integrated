"""Leave tables. People are plain user_id ints, no user table here."""
from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel


class LeaveRequest(TimeStampedModel, UserScopedModel):
    CATEGORY = [
        ("CL", "Casual Leave"), ("RH", "Restricted Holiday"),
        ("SCL", "Special Casual Leave"), ("EL", "Earned Leave"),
        ("COL", "Commuted Leave"), ("VL", "Vacation Leave"),
    ]
    STATUS = [
        ("draft", "Draft"), ("awaiting_substitute", "Awaiting Substitute"),
        ("unit_head_queue", "Unit Head Queue"),
        ("establishment", "Establishment"),
        ("final_decision", "Final Decision"),
        ("approved", "Approved"), ("rejected", "Rejected"),
        ("withdrawn", "Withdrawn"), ("cancelled", "Cancelled"),
    ]

    category = models.CharField(max_length=8, choices=CATEGORY)
    start_date = models.DateField()
    end_date = models.DateField()
    half_day = models.BooleanField(default=False)
    purpose = models.TextField(blank=True)
    station_leave = models.BooleanField(default=False)
    station_details = models.CharField(max_length=300, blank=True)
    substitute_user_id = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=24, choices=STATUS, default="draft")

    class Meta:
        db_table = "leave_request"
        indexes = [
            models.Index(fields=["user_id", "status"], name="leave_user_idx"),
            models.Index(fields=["status"], name="leave_status_idx"),
        ]

    def __str__(self):
        return f"leave#{self.pk} u{self.user_id} {self.category} {self.status}"


class LeaveTransition(models.Model):
    """Append-only audit of status change."""
    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE,
                                related_name="transitions")
    from_status = models.CharField(max_length=24)
    to_status = models.CharField(max_length=24)
    actor_user_id = models.IntegerField(null=True, blank=True)
    reason = models.CharField(max_length=300, blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "leave_transition"
        indexes = [models.Index(fields=["request", "at"], name="leave_tr_idx")]
