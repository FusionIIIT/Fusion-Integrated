from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel


class UserStorageQuota(TimeStampedModel):
    user_id = models.IntegerField(unique=True, db_index=True)
    allocated_quota_bytes = models.BigIntegerField(default=10737418240)
    used_storage_bytes = models.BigIntegerField(default=0)
    is_full = models.BooleanField(default=False)
    last_calculated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "badms_user_storage_quota"
        constraints = [
            models.CheckConstraint(
                condition=Q(allocated_quota_bytes__gte=0),
                name="chk_badms_quota_alloc_pos",
            ),
            models.CheckConstraint(
                condition=Q(used_storage_bytes__gte=0),
                name="chk_badms_quota_used_pos",
            ),
        ]
        indexes = [
            models.Index(fields=["is_full"], name="idx_badms_quota_is_full"),
        ]


class StorageLedgerEntry(TimeStampedModel):
    ENTRY_CREDIT = "credit"
    ENTRY_DEBIT = "debit"
    ENTRY_CHOICES = [
        (ENTRY_CREDIT, "Credit"),
        (ENTRY_DEBIT, "Debit"),
    ]

    quota = models.ForeignKey(
        UserStorageQuota,
        on_delete=models.CASCADE,
        related_name="ledger_entries",
    )
    amount_bytes = models.BigIntegerField()
    entry_type = models.CharField(max_length=20, choices=ENTRY_CHOICES)
    reference = models.CharField(max_length=200, blank=True)
    created_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "badms_storage_ledger_entry"
        ordering = ["created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(amount_bytes__gt=0),
                name="chk_badms_ledger_amount_pos",
            ),
            models.CheckConstraint(
                condition=Q(entry_type__in=["credit", "debit"]),
                name="chk_badms_ledger_entry_type",
            ),
        ]
        indexes = [
            models.Index(fields=["quota", "-created_at"], name="idx_badms_ledger_quota_cr"),
        ]


class StorageExtensionRequest(TimeStampedModel):
    STATUS_SUBMITTED = "submitted"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_CHOICES = [
        (STATUS_SUBMITTED, "Submitted"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
    ]

    requester_user_id = models.IntegerField(db_index=True)
    department = models.CharField(max_length=100)
    current_usage_bytes = models.BigIntegerField()
    current_quota_bytes = models.BigIntegerField()
    requested_extension_bytes = models.BigIntegerField()
    justification = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_SUBMITTED)
    hod_reviewed_by_user_id = models.IntegerField(null=True, blank=True)
    hod_decision_at = models.DateTimeField(null=True, blank=True)
    hod_remarks = models.TextField(blank=True)

    class Meta:
        db_table = "badms_storage_extension_request"
        constraints = [
            models.CheckConstraint(
                condition=Q(status__in=["submitted", "approved", "rejected"]),
                name="chk_badms_storext_status",
            ),
            models.CheckConstraint(
                condition=Q(requested_extension_bytes__gt=0),
                name="chk_badms_storext_req_pos",
            ),
        ]
        indexes = [
            models.Index(fields=["department", "status"], name="idx_badms_storext_dept_st"),
            models.Index(
                fields=["requester_user_id", "-created_at"], name="idx_badms_storext_user_cr"
            ),
        ]
