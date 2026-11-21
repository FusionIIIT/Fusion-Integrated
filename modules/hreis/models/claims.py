"""LTC/CPDA request details; no payment execution or file storage."""

from django.db import models
from django.db.models import Q


class ClaimDetail(models.Model):
    request = models.OneToOneField("HRRequest", on_delete=models.PROTECT, related_name="claim")
    claim_type = models.CharField(max_length=4, choices=[("ltc", "LTC"), ("cpda", "CPDA")])
    subtype = models.CharField(
        max_length=16,
        choices=[
            ("advance", "Advance"),
            ("reimbursement", "Reimbursement"),
        ],
    )
    prescribed_form_reference = models.CharField(max_length=250, blank=True)
    purpose = models.TextField(blank=True)
    amount = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True)
    hr_verified_by_user_id = models.IntegerField(null=True, blank=True)
    financial_verified_by_user_id = models.IntegerField(null=True, blank=True)
    financial_processing_details = models.JSONField(default=dict)

    class Meta:
        db_table = "hreis_claim"
        constraints = [
            models.CheckConstraint(
                condition=Q(amount__isnull=True) | Q(amount__gt=0), name="hr_claim_amount_positive"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.claim_type.upper()} claim {self.request_id}"


class ClaimDocument(models.Model):
    claim = models.ForeignKey(ClaimDetail, on_delete=models.PROTECT, related_name="documents")
    document_kind = models.CharField(max_length=80)
    secure_object_reference = models.CharField(max_length=300)
    integrity_digest = models.CharField(max_length=128)
    uploaded_by_user_id = models.IntegerField()
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "hreis_claim_document"
        indexes = [
            models.Index(fields=["claim", "recorded_at"], name="hr_claim_document_idx"),
        ]

    def __str__(self) -> str:
        return f"Claim document {self.pk} for {self.claim_id}"


class FinancialStatusProjection(models.Model):
    """Append-only attestation of an external claim status, never a payment order.

    BR-HR-018/022/027/035: each new status is an independent recorded event;
    ClaimDetail's JSON field is only the convenient latest-value projection.
    """
    claim = models.ForeignKey(
        ClaimDetail, on_delete=models.PROTECT, related_name="status_history"
    )
    event_key = models.CharField(max_length=180, unique=True)
    source_system = models.CharField(
        max_length=16, choices=[("finance", "Finance"), ("payroll", "Payroll")]
    )
    external_status_reference = models.CharField(max_length=250)
    financial_review_reference = models.CharField(max_length=250)
    payment_status = models.CharField(
        max_length=20,
        choices=[
            ("processing", "Processing"),
            ("payment_pending", "Payment pending"),
            ("paid", "Paid"),
            ("failed", "Failed"),
        ],
    )
    attested_by_user_id = models.IntegerField()
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "hreis_financial_status"
        indexes = [
            models.Index(fields=["claim", "recorded_at"], name="hr_finance_history_idx"),
        ]

    def __str__(self) -> str:
        return f"Financial status {self.payment_status} for claim {self.claim_id}"
