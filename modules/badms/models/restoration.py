from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel


class RestorationRequest(TimeStampedModel):
    CLASSIFICATION_CHOICES = [
        ("Routine", "Routine"),
        ("Sensitive", "Sensitive"),
        ("Critical", "Critical"),
        ("Archival", "Archival"),
    ]

    STATUS_REQUESTED_STANDARD = "requested_standard"
    STATUS_SENSITIVE_PENDING = "sensitive_pending_approval"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_RESTORED = "restored"
    STATUS_CHOICES = [
        (STATUS_REQUESTED_STANDARD, "Requested Standard"),
        (STATUS_SENSITIVE_PENDING, "Sensitive Pending Approval"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_RESTORED, "Restored"),
    ]

    requester_user_id = models.IntegerField(db_index=True)
    department = models.CharField(max_length=100)
    archival_request_id = models.BigIntegerField(db_index=True)
    classification = models.CharField(max_length=20, choices=CLASSIFICATION_CHOICES)
    target_destination = models.CharField(max_length=255)
    status = models.CharField(
        max_length=40, choices=STATUS_CHOICES, default=STATUS_REQUESTED_STANDARD
    )
    approved_by_user_id = models.IntegerField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    executed_by_user_id = models.IntegerField(null=True, blank=True)
    restored_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        db_table = "badms_restoration_request"
        constraints = [
            models.CheckConstraint(
                condition=Q(
                    status__in=[
                        "requested_standard",
                        "sensitive_pending_approval",
                        "approved",
                        "rejected",
                        "restored",
                    ]
                ),
                name="chk_badms_rest_status",
            ),
        ]
        indexes = [
            models.Index(fields=["status", "-created_at"], name="idx_badms_rest_st_cr"),
        ]
