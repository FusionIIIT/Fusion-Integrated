"""Medical Bill Reimbursement models (CFR-PHC-003, CFR-PHC-004, CFR-PHC-005)."""
from django.db import models

from core.db.mixins import TimeStampedModel
from modules.phc.domain.entities import ReimbursementStatus
from .patient_records import Prescription


class ReimbursementClaim(TimeStampedModel):
    """Reimbursement claim lifecycle (CW-PHC-01, BW-PHC-01, BW-PHC-02)."""
    STATUS_CHOICES = [
        (s.value, s.value) for s in ReimbursementStatus
    ]

    claim_number = models.CharField(max_length=64, unique=True, db_index=True)
    claimant_user_id = models.IntegerField(db_index=True)
    prescription = models.ForeignKey(Prescription, on_delete=models.PROTECT, related_name="claims")
    expense_date = models.DateField()
    amount_claimed = models.DecimalField(max_digits=10, decimal_places=2)
    amount_approved = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    bills_document_url = models.CharField(max_length=500, blank=True)
    status = models.CharField(
        max_length=40,
        choices=STATUS_CHOICES,
        default=ReimbursementStatus.PENDING_PHC_REVIEW.value,
        db_index=True,
    )
    remarks = models.TextField(blank=True)

    class Meta:
        db_table = "phc_reimbursement_claims"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Claim {self.claim_number} ({self.status}) - ₹{self.amount_claimed}"


class ReimbursementActionHistory(models.Model):
    """Immutable progression audit history for claims (AFR-PHC-022, 023)."""
    claim = models.ForeignKey(ReimbursementClaim, on_delete=models.CASCADE, related_name="history")
    action = models.CharField(max_length=64)
    from_status = models.CharField(max_length=40)
    to_status = models.CharField(max_length=40)
    actor_user_id = models.IntegerField()
    actor_role = models.CharField(max_length=64)
    comments = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "phc_reimbursement_action_history"
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.claim.claim_number}: {self.from_status} -> {self.to_status} by User {self.actor_user_id}"
