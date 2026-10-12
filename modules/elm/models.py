from django.conf import settings
from django.db import models

from core.db.mixins import TimeStampedModel
from modules.directory.models import UserRef


class LeaveRequest(TimeStampedModel):
    class Category(models.TextChoices):
        CL = "CL", "Casual Leave"
        RH = "RH", "Restricted Holiday"
        SCL = "SCL", "Special Casual Leave"
        EL = "EL", "Earned Leave"
        COL = "COL", "Commuted Leave"
        VL = "VL", "Vacation Leave"
        STATION = "STATION", "Station Leave"

    class Status(models.TextChoices):
        AWAITING_SUBSTITUTE = "awaiting_substitute", "Awaiting Substitute Response"
        APPLICANT_ACTION = "applicant_action", "Applicant Action Required"
        UNIT_HEAD_REVIEW = "unit_head_review", "Awaiting Unit Head Review"
        ESTABLISHMENT_ROUTING = "establishment_routing", "Awaiting Establishment Routing"
        FINAL_SANCTION = "final_sanction", "Awaiting Final Sanction Decision"
        DIRECTOR_SANCTION = "director_sanction", "Awaiting Director Self-Sanction"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        WITHDRAWN = "withdrawn", "Withdrawn"

    employee = models.ForeignKey(
        UserRef, on_delete=models.PROTECT, related_name="elm_leave_requests"
    )
    category = models.CharField(max_length=10, choices=Category.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    substitute = models.ForeignKey(
        UserRef, null=True, blank=True, on_delete=models.PROTECT,
        related_name="elm_substitute_requests",
    )
    substitute_required = models.BooleanField(default=False)
    status = models.CharField(
        max_length=32, choices=Status.choices,
        default=Status.UNIT_HEAD_REVIEW, db_index=True,
    )
    unit_head_recommended = models.BooleanField(null=True, blank=True)
    establishment_required = models.BooleanField(default=False)
    final_decision_by = models.ForeignKey(
        UserRef, null=True, blank=True, on_delete=models.PROTECT,
        related_name="elm_final_decisions",
    )
    decision_note = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValidationError({"end_date": "End date cannot precede start date."})
        if self.substitute_required and not self.substitute_id:
            raise ValidationError({
                "substitute": "A substitute is required for this application."
            })
        if self.substitute_id and self.employee_id == self.substitute_id:
            raise ValidationError({
                "substitute": "An employee cannot be their own substitute."
            })


class SubstituteResponse(TimeStampedModel):
    class Decision(models.TextChoices):
        ACCEPTED = "accepted", "Accepted"
        DECLINED = "declined", "Declined"

    leave_request = models.ForeignKey(
        LeaveRequest, on_delete=models.CASCADE, related_name="substitute_responses"
    )
    substitute = models.ForeignKey(
        UserRef, on_delete=models.PROTECT, related_name="elm_responses"
    )
    decision = models.CharField(max_length=10, choices=Decision.choices)
    note = models.TextField(blank=True)


class LeaveDecision(TimeStampedModel):
    leave_request = models.ForeignKey(
        LeaveRequest, on_delete=models.CASCADE, related_name="decisions"
    )
    actor = models.ForeignKey(UserRef, on_delete=models.PROTECT)
    stage = models.CharField(max_length=32)
    decision = models.CharField(max_length=20)
    note = models.TextField(blank=True)
