from django.db import models
from core.db.mixins import TimeStampedModel
from modules.elm.models.leave_requests import LeaveRequest


class SubstituteResponse(TimeStampedModel):
    """Substitute response record for responsibility coverage.

    Implements BR-EL-014, BR-EL-015, CW-EL-01.
    Connects a leave request to a nominated substitute employee user.
    """
    RESPONSE_CHOICES = [
        ("PENDING", "Pending"),
        ("ACCEPTED", "Accepted"),
        ("DECLINED", "Declined"),
    ]

    leave_request = models.ForeignKey(
        LeaveRequest, on_delete=models.CASCADE, related_name="substitute_responses"
    )
    substitute_user_id = models.IntegerField(db_index=True)
    status = models.CharField(
        max_length=16,
        choices=RESPONSE_CHOICES,
        default="PENDING",
        db_index=True,
    )
    remarks = models.CharField(max_length=500, blank=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "elm_substitute_response"
        constraints = [
            models.UniqueConstraint(
                fields=["leave_request", "substitute_user_id"],
                name="unique_request_substitute",
            ),
        ]
        indexes = [
            models.Index(
                fields=["substitute_user_id", "status"],
                name="substitute_pending_idx",
            ),
        ]

    def __str__(self):
        return f"Substitute {self.substitute_user_id} for request {self.leave_request_id}: {self.status}"
