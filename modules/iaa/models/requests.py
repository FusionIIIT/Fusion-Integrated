from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel


class RequestType(models.TextChoices):
    EXPENSE = "expense", "Expense Request"
    VOUCHER = "voucher", "Voucher Request"


class RequestStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    SUBMITTED = "submitted", "Submitted"
    QUERY_RAISED = "query_raised", "Query Raised"
    QUERY_RESPONDED = "query_responded", "Query Responded"
    FINANCE_VALIDATED = "finance_validated", "Finance Validated"
    APPROVAL_PENDING = "approval_pending", "Approval Pending"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    ESCALATED = "escalated", "Escalated"
    RECORDED = "recorded", "Recorded"


class ExpenseVoucherRequest(TimeStampedModel, UserScopedModel):
    department = models.CharField(max_length=64, db_index=True)
    request_type = models.CharField(
        max_length=32, choices=RequestType.choices, default=RequestType.EXPENSE
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    status = models.CharField(
        max_length=32, choices=RequestStatus.choices, default=RequestStatus.DRAFT, db_index=True
    )
    current_approval_level = models.PositiveIntegerField(default=1)
    required_approval_levels = models.PositiveIntegerField(default=1)
    assigned_approver_role = models.CharField(max_length=64, blank=True)
    assigned_approver_id = models.IntegerField(null=True, blank=True, db_index=True)
    approval_assigned_at = models.DateTimeField(null=True, blank=True)
    is_locked = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"[{self.request_type.upper()}-{self.id}] {self.title} ({self.status})"


class ExpenseItem(TimeStampedModel):
    request = models.ForeignKey(
        ExpenseVoucherRequest, on_delete=models.CASCADE, related_name="items"
    )
    description = models.CharField(max_length=255)
    category = models.CharField(max_length=64, default="General")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    receipt_reference = models.CharField(max_length=128, blank=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.description} ({self.amount})"


class SupportingDocument(TimeStampedModel):
    target_type = models.CharField(max_length=32, db_index=True)
    target_id = models.IntegerField(db_index=True)
    file_name = models.CharField(max_length=255)
    file_url = models.CharField(max_length=512)
    document_type = models.CharField(max_length=64, default="receipt")

    class Meta:
        ordering = ["-created_at"]
