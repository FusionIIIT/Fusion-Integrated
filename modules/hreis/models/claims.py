"""LTC and CPDA models (BR-HR-016 to BR-HR-022, BR-HR-035)."""
from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel
from modules.hreis.domain.claims import (
    ClaimStatus,
    ClaimType,
    PaymentStatus,
    VerificationStatus,
)


class LtcRequest(TimeStampedModel, UserScopedModel):
    """Leave Travel Concession claim (Advance or Reimbursement)."""

    user_id = models.IntegerField(db_index=True)
    request_type = models.CharField(
        max_length=32,
        choices=[(t.value, t.name.title()) for t in ClaimType],
    )
    block_year = models.CharField(max_length=32, db_index=True)
    travel_from = models.CharField(max_length=128)
    travel_to = models.CharField(max_length=128)
    travel_start_date = models.DateField()
    travel_end_date = models.DateField()
    estimated_amount = models.DecimalField(max_digits=10, decimal_places=2)
    claimed_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    passed_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    supporting_documents = models.JSONField(default=list, blank=True)

    verification_status = models.CharField(
        max_length=32,
        choices=[(v.value, v.name.title()) for v in VerificationStatus],
        default=VerificationStatus.PENDING.value,
        db_index=True,
    )
    verification_remarks = models.TextField(blank=True)

    status = models.CharField(
        max_length=32,
        choices=[(s.value, s.name.title()) for s in ClaimStatus],
        default=ClaimStatus.SUBMITTED.value,
        db_index=True,
    )
    current_authority_role = models.CharField(max_length=64, default="hod", db_index=True)
    approval_history = models.JSONField(default=list, blank=True)

    payment_status = models.CharField(
        max_length=32,
        choices=[(p.value, p.name.title()) for p in PaymentStatus],
        default=PaymentStatus.UNPAID.value,
        db_index=True,
    )
    payment_reference = models.CharField(max_length=128, blank=True)
    settlement_details = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "hreis_ltc_request"
        verbose_name = "LTC Request"
        verbose_name_plural = "LTC Requests"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"LTC(id={self.id}, user={self.user_id}, type={self.request_type}, status={self.status})"


class CpdaRequest(TimeStampedModel, UserScopedModel):
    """Cumulative Professional Development Allowance claim."""

    user_id = models.IntegerField(db_index=True)
    request_type = models.CharField(
        max_length=32,
        choices=[(t.value, t.name.title()) for t in ClaimType],
    )
    purpose = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    passed_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    supporting_documents = models.JSONField(default=list, blank=True)

    verification_status = models.CharField(
        max_length=32,
        choices=[(v.value, v.name.title()) for v in VerificationStatus],
        default=VerificationStatus.PENDING.value,
        db_index=True,
    )
    verification_remarks = models.TextField(blank=True)

    status = models.CharField(
        max_length=32,
        choices=[(s.value, s.name.title()) for s in ClaimStatus],
        default=ClaimStatus.SUBMITTED.value,
        db_index=True,
    )
    current_authority_role = models.CharField(max_length=64, default="hod", db_index=True)
    approval_history = models.JSONField(default=list, blank=True)

    disbursement_status = models.CharField(
        max_length=32,
        choices=[(p.value, p.name.title()) for p in PaymentStatus],
        default=PaymentStatus.UNPAID.value,
        db_index=True,
    )
    disbursement_details = models.JSONField(default=dict, blank=True)

    class Meta:
        db_table = "hreis_cpda_request"
        verbose_name = "CPDA Request"
        verbose_name_plural = "CPDA Requests"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"CPDA(id={self.id}, user={self.user_id}, purpose={self.purpose}, status={self.status})"
