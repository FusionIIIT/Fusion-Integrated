from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel


class TAClaimStatus(models.TextChoices):
    SUBMITTED = "submitted", "Submitted"
    QUERY_RAISED = "query_raised", "Query Raised"
    QUERY_RESPONDED = "query_responded", "Query Responded"
    VERIFIED = "verified", "Verified"
    APPROVAL_PENDING = "approval_pending", "Approval Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    ESCALATED = "escalated", "Escalated"
    RECORDED = "recorded", "Recorded"


class TAClaim(TimeStampedModel, UserScopedModel):
    department = models.CharField(max_length=64, db_index=True)
    purpose = models.CharField(max_length=255)
    departure_date = models.DateField()
    arrival_date = models.DateField()
    source_location = models.CharField(max_length=128)
    destination_location = models.CharField(max_length=128)
    claimed_amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(
        max_length=32, choices=TAClaimStatus.choices, default=TAClaimStatus.SUBMITTED, db_index=True
    )
    is_high_value = models.BooleanField(default=False)
    assigned_approver_role = models.CharField(max_length=64, blank=True)
    assigned_approver_id = models.IntegerField(null=True, blank=True, db_index=True)
    approval_assigned_at = models.DateTimeField(null=True, blank=True)
    is_locked = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"[TA-{self.id}] {self.purpose} ({self.claimed_amount})"


class TAExpenseItem(TimeStampedModel):
    claim = models.ForeignKey(TAClaim, on_delete=models.CASCADE, related_name="items")
    expense_type = models.CharField(max_length=64)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    details = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["id"]
