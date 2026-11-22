from django.db import models

from core.db.mixins import TimeStampedModel


class OfficeActionType(models.TextChoices):
    FER = "fer", "First Examination Report"
    SER = "ser", "Second Examination Report"
    HEARING_NOTICE = "hearing_notice", "Hearing Notice"
    THIRD_PARTY_OBSERVATION = "third_party", "Third-Party Pre-Grant Opposition"


class ResponseStatus(models.TextChoices):
    PENDING = "pending", "Pending Response Drafting"
    DRAFTED = "drafted", "Response Drafted by Attorney"
    APPLICANT_APPROVED = "applicant_approved", "Approved by Principal Inventor"
    SUBMITTED_TO_IPO = "submitted", "Filed with Patent Office"
    DEADLINE_EXPIRED = "expired", "Statutory Deadline Expired"


class OfficeAction(TimeStampedModel):
    """Statutory communication or examination report received from Patent Office."""

    application = models.ForeignKey(
        "pms.PatentApplication",
        on_delete=models.CASCADE,
        related_name="office_actions",
    )
    action_type = models.CharField(
        max_length=32,
        choices=OfficeActionType.choices,
        default=OfficeActionType.FER,
    )
    issuing_authority = models.CharField(max_length=128, default="Indian Patent Office")
    issue_date = models.DateField()
    statutory_deadline = models.DateField(db_index=True)
    objections_summary = models.TextField()
    response_draft = models.TextField(blank=True, default="")
    response_status = models.CharField(
        max_length=32,
        choices=ResponseStatus.choices,
        default=ResponseStatus.PENDING,
    )
    response_submitted_date = models.DateField(null=True, blank=True)
    handled_by_attorney_id = models.IntegerField(db_index=True)

    class Meta:
        db_table = "pms_office_action"
        ordering = ["statutory_deadline"]

    def __str__(self) -> str:
        return f"{self.action_type} for App #{self.application_id} (Due: {self.statutory_deadline})"
