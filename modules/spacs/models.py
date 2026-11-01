"""SPACS scholarship application and supporting-document tables."""
import uuid

from django.db import models
from django.utils import timezone

from core.db.mixins import TimeStampedModel


class ScholarshipApplication(TimeStampedModel):
    STATUS_DRAFT = "draft"
    STATUS_SUBMITTED = "submitted"
    STATUS_UNDER_VERIFICATION = "under_verification"
    STATUS_CORRECTION_REQUIRED = "correction_required"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_WITHDRAWN = "withdrawn"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_SUBMITTED, "Submitted"),
        (STATUS_UNDER_VERIFICATION, "Under verification"),
        (STATUS_CORRECTION_REQUIRED, "Correction required"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_WITHDRAWN, "Withdrawn"),
    ]

    VERIFICATION_PENDING = "pending"
    VERIFICATION_VERIFIED = "verified"
    VERIFICATION_ISSUES_FOUND = "issues_found"
    VERIFICATION_STATUS_CHOICES = [
        (VERIFICATION_PENDING, "Pending"),
        (VERIFICATION_VERIFIED, "Verified"),
        (VERIFICATION_ISSUES_FOUND, "Issues found"),
    ]

    application_id = models.UUIDField(
        default=uuid.uuid4, unique=True, editable=False,
    )
    scheme_id = models.CharField(max_length=64, db_index=True)
    # IAM identities are external to this database; keep the ID unconstrained.
    student_id = models.IntegerField(db_index=True)
    submission_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=24, choices=STATUS_CHOICES, default=STATUS_DRAFT, db_index=True,
    )
    documents_list = models.JSONField(default=list, blank=True)

    assigned_assistant_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    verification_status = models.CharField(
        max_length=16,
        choices=VERIFICATION_STATUS_CHOICES,
        default=VERIFICATION_PENDING,
    )
    verification_findings = models.JSONField(default=dict, blank=True)
    verified_by_user_id = models.IntegerField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    decision_note = models.TextField(blank=True)
    decided_by_user_id = models.IntegerField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "spacs_scholarship_application"
        indexes = [
            models.Index(
                fields=["student_id", "status"],
                name="spacs_app_student_status_idx",
            ),
            models.Index(
                fields=["assigned_assistant_user_id", "status"],
                name="spacs_app_assignee_status_idx",
            ),
        ]

    def __str__(self) -> str:
        return str(self.application_id)


class SupportingDocument(TimeStampedModel):
    VALIDITY_PENDING = "pending"
    VALIDITY_VALID = "valid"
    VALIDITY_INVALID = "invalid"
    VALIDITY_EXPIRED = "expired"
    VALIDITY_STATUS_CHOICES = [
        (VALIDITY_PENDING, "Pending"),
        (VALIDITY_VALID, "Valid"),
        (VALIDITY_INVALID, "Invalid"),
        (VALIDITY_EXPIRED, "Expired"),
    ]

    document_id = models.UUIDField(
        default=uuid.uuid4, unique=True, editable=False,
    )
    document_type = models.CharField(max_length=64, db_index=True)
    file_url = models.URLField(max_length=1000)
    upload_date = models.DateTimeField(default=timezone.now)
    is_reusable = models.BooleanField(default=False)
    validity_status = models.CharField(
        max_length=16,
        choices=VALIDITY_STATUS_CHOICES,
        default=VALIDITY_PENDING,
        db_index=True,
    )
    owner_user_id = models.IntegerField(db_index=True)

    class Meta:
        db_table = "spacs_supporting_document"
        indexes = [
            models.Index(
                fields=["owner_user_id", "document_type"],
                name="spacs_doc_owner_type_idx",
            ),
        ]

    def __str__(self) -> str:
        return str(self.document_id)
