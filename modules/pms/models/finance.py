from django.db import models
from django.db.models import CheckConstraint, Q

from core.db.mixins import TimeStampedModel


class TransactionType(models.TextChoices):
    OFFICIAL_FILING_FEE = "filing_fee", "Official Patent Office Filing Fee"
    ATTORNEY_PROFESSIONAL_FEE = "attorney_fee", "Patent Attorney Professional Service Fee"
    PATENTABILITY_SEARCH_FEE = "search_fee", "Patentability Search & Analytics Fee"
    EXAMINATION_REQUEST_FEE = "examination_fee", "Request for Examination (RFE) Fee"
    HEARING_ATTENDANCE_FEE = "hearing_fee", "Hearing Representation Fee"
    GRANT_ISSUANCE_FEE = "grant_fee", "Grant & Certificate Issuance Fee"
    MAINTENANCE_ANNUITY_FEE = "renewal_fee", "Patent Maintenance / Annuity Renewal Fee"
    CORRECTION_REVERSAL = "correction_reversal", "Reversing Entry for Previous Error"


class PaymentStatus(models.TextChoices):
    RECORDED = "recorded", "Transaction Recorded"
    DISBURSED = "disbursed", "Disbursed / Paid by Institute Finance"
    RECONCILED = "reconciled", "Bank & Invoice Reconciled"
    REVERSED = "reversed", "Reversed / Corrected"


class PatentFinancialTransaction(TimeStampedModel):
    """Append-only ledger for all patent expenses, disbursements, and reversing entries.
    
    In accordance with §2.7, financial balances are never stored as mutable columns.
    All balances are computed as sums over this immutable ledger.
    """

    application = models.ForeignKey(
        "pms.PatentApplication",
        on_delete=models.CASCADE,
        related_name="financial_transactions",
    )
    transaction_type = models.CharField(max_length=32, choices=TransactionType.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=8, default="INR")
    payment_status = models.CharField(
        max_length=32,
        choices=PaymentStatus.choices,
        default=PaymentStatus.RECORDED,
    )
    reference_no = models.CharField(max_length=128, db_index=True)
    recorded_by_user_id = models.IntegerField(db_index=True)
    effective_date = models.DateField()
    description = models.CharField(max_length=512, blank=True, default="")
    reversal_of_transaction_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "pms_financial_transaction"
        ordering = ["-created_at"]
        constraints = [
            CheckConstraint(
                check=~Q(reference_no=""),
                name="pms_financial_ref_non_empty",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.transaction_type}: {self.amount} {self.currency} ({self.reference_no})"
