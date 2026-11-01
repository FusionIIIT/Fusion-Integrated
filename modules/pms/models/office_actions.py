"""Patent office communications, office actions, and responses."""

from django.db import models

from core.db.mixins import TimeStampedModel
from modules.pms.models.applications import PatentApplication


class OfficeAction(TimeStampedModel):
    """Office action / examination report received from patent office (CW-PMS-03, BW-PMS-12, 13)."""

    application = models.ForeignKey(
        PatentApplication, on_delete=models.CASCADE, related_name="office_actions"
    )
    action_number = models.CharField(max_length=100)
    issue_date = models.DateField()
    response_deadline = models.DateField(db_index=True)
    action_type = models.CharField(
        max_length=100
    )  # first_examination_report, objection, hearing_notice
    description = models.TextField()
    status = models.CharField(max_length=50, default="office_action_recorded", db_index=True)
    recorded_by_user_id = models.IntegerField()

    class Meta:
        db_table = "pms_office_action"
        ordering = ["-response_deadline"]
        indexes = [
            models.Index(fields=["application", "status"]),
        ]

    def __str__(self) -> str:
        return f"OA {self.action_number} - App {self.application_id} (Due {self.response_deadline})"


class OfficeActionResponse(TimeStampedModel):
    """Response prepared by attorney, with applicant review when required (BR-PMS-146)."""

    office_action = models.ForeignKey(
        OfficeAction, on_delete=models.CASCADE, related_name="responses"
    )
    attorney_user_id = models.IntegerField(db_index=True)
    draft_text = models.TextField()
    requires_applicant_approval = models.BooleanField(default=True)
    applicant_approved = models.BooleanField(default=False)
    applicant_approved_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    submission_details = models.TextField(blank=True)

    class Meta:
        db_table = "pms_office_action_response"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Response to OA {self.office_action_id} (Approved: {self.applicant_approved})"


class ExtensionRequest(TimeStampedModel):
    """Extension of time request filed with patent office (UC-PMS-015 alternative flow)."""

    office_action = models.ForeignKey(
        OfficeAction, on_delete=models.CASCADE, related_name="extension_requests"
    )
    attorney_user_id = models.IntegerField()
    requested_days = models.IntegerField(default=30)
    reason = models.TextField()
    filed_date = models.DateField(auto_now_add=True)
    is_granted = models.BooleanField(default=True)
    new_deadline = models.DateField()

    class Meta:
        db_table = "pms_extension_request"
        ordering = ["-filed_date"]

    def __str__(self) -> str:
        return f"Extension for OA {self.office_action_id}: +{self.requested_days} days"
