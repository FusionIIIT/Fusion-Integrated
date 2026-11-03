from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel
from modules.oap.domain import constants as c


class StudentLeaveApplication(TimeStampedModel, UserScopedModel):
    """Student leave application model (OA-UC-01, OA-UC-03, BW-OAP-01, BW-OAP-02)."""

    department = models.CharField(max_length=100)
    programme = models.CharField(max_length=20, default=c.PROGRAMME_UG)
    leave_type = models.CharField(max_length=50, default="Casual Leave")
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()

    status = models.CharField(
        max_length=50,
        choices=[(s, s) for s in c.LEAVE_STATES],
        default=c.LEAVE_SUBMITTED,
        db_index=True,
    )
    decision_by_user_id = models.IntegerField(null=True, blank=True)
    decision_remarks = models.TextField(blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]


class LeaveAttachment(TimeStampedModel):
    """Optional supporting attachments for student leave applications (AFR-OAP-010)."""

    leave_application = models.ForeignKey(
        StudentLeaveApplication,
        on_delete=models.CASCADE,
        related_name="attachments",
    )
    file_name = models.CharField(max_length=255)
    file_url = models.CharField(max_length=500)
