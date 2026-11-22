from django.db import models
from django.db.models import CheckConstraint, Index, Q

from core.db.mixins import TimeStampedModel


class ApplicationStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    SUBMITTED = "submitted", "Submitted"
    UNDER_REVIEW = "under_review", "Under Review"
    NEEDS_REVISION = "needs_revision", "Needs Revision"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    APPEALED = "appealed", "Appealed"
    ATTORNEY_ASSIGNED = "attorney_assigned", "Attorney Assigned"
    FILING_IN_PROGRESS = "filing_in_progress", "Filing In Progress"
    FILED = "filed", "Filed (External)"
    PUBLISHED = "published", "Published"
    FER_RECEIVED = "fer_received", "FER / Office Action Received"
    FER_RESPONDED = "fer_responded", "FER Responded"
    HEARING_SCHEDULED = "hearing_scheduled", "Oral Hearing Scheduled"
    GRANTED = "granted", "Granted"
    REFUSED = "refused", "Refused by Patent Office"
    WITHDRAWN = "withdrawn", "Withdrawn by Applicant"
    ABANDONED = "abandoned", "Statutorily Abandoned"
    MAINTENANCE = "maintenance", "Post-Grant Maintenance"
    EXPIRED = "expired", "Statutorily Expired / Lapsed"


class FilingType(models.TextChoices):
    PROVISIONAL = "provisional", "Provisional Specification"
    COMPLETE = "complete", "Complete Specification"
    PCT = "pct", "PCT International Application"
    CONVENTION = "convention", "Convention Application"


class PatentApplication(TimeStampedModel):
    """Core aggregate entity representing a patent application throughout its lifecycle."""

    application_no = models.CharField(max_length=64, unique=True, db_index=True)
    title = models.CharField(max_length=512)
    abstract = models.TextField()
    detailed_description = models.TextField(blank=True, default="")
    claims = models.TextField(blank=True, default="")
    field_of_invention = models.CharField(max_length=256, blank=True, default="")
    applicant_user_id = models.IntegerField(db_index=True)
    status = models.CharField(
        max_length=32,
        choices=ApplicationStatus.choices,
        default=ApplicationStatus.DRAFT,
        db_index=True,
    )
    filing_type = models.CharField(
        max_length=32,
        choices=FilingType.choices,
        default=FilingType.PROVISIONAL,
    )
    official_filing_number = models.CharField(max_length=64, blank=True, default="")
    official_filing_date = models.DateField(null=True, blank=True)
    grant_number = models.CharField(max_length=64, blank=True, default="")
    grant_date = models.DateField(null=True, blank=True)
    assigned_director_id = models.IntegerField(null=True, blank=True, db_index=True)
    assigned_attorney_id = models.IntegerField(null=True, blank=True, db_index=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "pms_patent_application"
        ordering = ["-created_at"]
        constraints = [
            CheckConstraint(check=~Q(title=""), name="pms_app_title_non_empty"),
            CheckConstraint(
                check=Q(applicant_user_id__gt=0),
                name="pms_app_valid_applicant_user_id",
            ),
        ]
        indexes = [
            Index(fields=["status", "applicant_user_id"], name="pms_app_status_applicant_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.application_no} - {self.title[:50]}"
