from django.db import models

from modules.elm.domain import (
    APPLICANT_ACTION_REQUIRED,
    APPROVED,
    AWAITING_DIRECTOR_SELF_SANCTION,
    AWAITING_ESTABLISHMENT_ROUTING,
    AWAITING_FINAL_SANCTION,
    AWAITING_SUBSTITUTE_RESPONSE,
    AWAITING_UNIT_HEAD_REVIEW,
    REJECTED,
    WITHDRAWN,
)

from .leave_types import LeaveType


class LeaveApplication(models.Model):
    STATUS_CHOICES = [
        (AWAITING_SUBSTITUTE_RESPONSE, "Awaiting Substitute Response"),
        (APPLICANT_ACTION_REQUIRED, "Applicant Action Required"),
        (AWAITING_UNIT_HEAD_REVIEW, "Awaiting Unit Head Review"),
        (AWAITING_ESTABLISHMENT_ROUTING, "Awaiting Establishment Routing"),
        (AWAITING_FINAL_SANCTION, "Awaiting Final Sanction"),
        (AWAITING_DIRECTOR_SELF_SANCTION, "Awaiting Director Self Sanction"),
        (APPROVED, "Approved"),
        (REJECTED, "Rejected"),
        (WITHDRAWN, "Withdrawn"),
    ]

    user_id = models.IntegerField()
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    purpose = models.TextField()
    station_leave_details = models.JSONField(default=dict, blank=True)
    substitute_id = models.IntegerField(null=True, blank=True)
    status = models.CharField(
        max_length=40, default=AWAITING_UNIT_HEAD_REVIEW, choices=STATUS_CHOICES
    )
    unit_head_recommendation = models.CharField(max_length=20, blank=True, default="")

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    decision_maker_id = models.IntegerField(null=True, blank=True)
    decision_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Leave Application"
        db_table = "elm_leave_application"

    def __str__(self):
        return f"LeaveApp-{self.id} (User {self.user_id})"
