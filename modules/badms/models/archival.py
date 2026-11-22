from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel


class ArchivalRequest(TimeStampedModel):
    CLASSIFICATION_ROUTINE = "Routine"
    CLASSIFICATION_SENSITIVE = "Sensitive"
    CLASSIFICATION_CRITICAL = "Critical"
    CLASSIFICATION_ARCHIVAL = "Archival"
    CLASSIFICATION_CHOICES = [
        (CLASSIFICATION_ROUTINE, "Routine"),
        (CLASSIFICATION_SENSITIVE, "Sensitive"),
        (CLASSIFICATION_CRITICAL, "Critical"),
        (CLASSIFICATION_ARCHIVAL, "Archival"),
    ]

    STATUS_SUBMITTED = "submitted"
    STATUS_REJECTED = "rejected"
    STATUS_HOD_APPROVED = "hod_approved"
    STATUS_CLASSIFIED_NON_SENSITIVE = "classified_non_sensitive"
    STATUS_CLASSIFIED_SENSITIVE = "classified_sensitive"
    STATUS_SENSITIVE_ENCRYPTED = "sensitive_archive_encrypted"
    STATUS_SPECIAL_ARCHIVED = "special_archived"
    STATUS_CHOICES = [
        (STATUS_SUBMITTED, "Submitted"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_HOD_APPROVED, "HoD Approved"),
        (STATUS_CLASSIFIED_NON_SENSITIVE, "Classified Non-Sensitive"),
        (STATUS_CLASSIFIED_SENSITIVE, "Classified Sensitive"),
        (STATUS_SENSITIVE_ENCRYPTED, "Sensitive Archive Encrypted"),
        (STATUS_SPECIAL_ARCHIVED, "Special Archived"),
    ]

    requester_user_id = models.IntegerField(db_index=True)
    department = models.CharField(max_length=100)
    file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=50)
    file_size_bytes = models.BigIntegerField()
    reason = models.TextField()
    file_storage_path = models.CharField(max_length=500)
    initial_classification = models.CharField(
        max_length=20, choices=CLASSIFICATION_CHOICES, default=CLASSIFICATION_ROUTINE
    )
    authoritative_classification = models.CharField(
        max_length=20, choices=CLASSIFICATION_CHOICES, blank=True, default=""
    )
    status = models.CharField(max_length=40, choices=STATUS_CHOICES, default=STATUS_SUBMITTED)
    hod_reviewed_by_user_id = models.IntegerField(null=True, blank=True)
    hod_decision_at = models.DateTimeField(null=True, blank=True)
    hod_remarks = models.TextField(blank=True)
    sysadmin_classified_by_user_id = models.IntegerField(null=True, blank=True)
    classified_at = models.DateTimeField(null=True, blank=True)
    encryption_algorithm = models.CharField(max_length=50, blank=True)
    is_encrypted = models.BooleanField(default=False)
    encrypted_by_user_id = models.IntegerField(null=True, blank=True)
    encrypted_at = models.DateTimeField(null=True, blank=True)
    is_special_archival = models.BooleanField(default=False)
    retention_policy_ref = models.CharField(max_length=100, blank=True)

    class Meta:
        db_table = "badms_archival_request"
        constraints = [
            models.CheckConstraint(
                condition=Q(
                    status__in=[
                        "submitted",
                        "rejected",
                        "hod_approved",
                        "classified_non_sensitive",
                        "classified_sensitive",
                        "sensitive_archive_encrypted",
                        "special_archived",
                    ]
                ),
                name="chk_badms_arch_status",
            ),
        ]
        indexes = [
            models.Index(fields=["department", "status"], name="idx_badms_arch_dept_status"),
            models.Index(
                fields=["requester_user_id", "-created_at"], name="idx_badms_arch_req_created"
            ),
        ]
