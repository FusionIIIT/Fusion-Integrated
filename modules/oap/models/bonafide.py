"""Domain model and certificate generation for bonafide certificate requests."""
from __future__ import annotations

import uuid

from django.db import models
from django.utils import timezone

from modules.oap.domain.exceptions import InvalidStateTransitionError


class BonafidePurpose(models.TextChoices):
    BANK_LOAN = "BANK_LOAN", "Bank Loan Application"
    PASSPORT = "PASSPORT", "Passport Verification"
    VISA = "VISA", "Visa Application"
    INTERNSHIP = "INTERNSHIP", "Internship / External Project"
    GENERAL = "GENERAL", "General Verification"


class BonafideStatus(models.TextChoices):
    PENDING = "PENDING", "Pending Verification"
    APPROVED = "APPROVED", "Approved & Issued"
    REJECTED = "REJECTED", "Rejected"


class BonafideRequest(models.Model):
    student_id = models.CharField(max_length=32, db_index=True)
    purpose = models.CharField(
        max_length=32, choices=BonafidePurpose.choices, default=BonafidePurpose.GENERAL
    )
    details = models.TextField(default="", blank=True)
    status = models.CharField(
        max_length=32, choices=BonafideStatus.choices, default=BonafideStatus.PENDING
    )
    certificate_number = models.CharField(max_length=64, unique=True, null=True, blank=True)
    issued_at = models.DateTimeField(null=True, blank=True)
    issued_by = models.CharField(max_length=32, default="", blank=True)
    rejection_reason = models.TextField(default="", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "oap_bonafide_request"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Bonafide {self.pk} - {self.student_id} ({self.status})"

    def approve_and_issue(self, issued_by: str, remarks: str = "") -> str:
        if self.status != BonafideStatus.PENDING:
            raise InvalidStateTransitionError(
                f"Cannot approve bonafide request in status '{self.status}'."
            )
        self.status = BonafideStatus.APPROVED
        self.issued_by = issued_by
        self.issued_at = timezone.now()
        cert_num = f"IIITDMJ/OAP/BONA/{timezone.now().year}/{uuid.uuid4().hex[:8].upper()}"
        self.certificate_number = cert_num
        self.save(update_fields=["status", "issued_by", "issued_at", "certificate_number"])
        return cert_num

    def reject(self, issued_by: str, reason: str):
        if self.status != BonafideStatus.PENDING:
            raise InvalidStateTransitionError(
                f"Cannot reject bonafide request in status '{self.status}'."
            )
        self.status = BonafideStatus.REJECTED
        self.issued_by = issued_by
        self.rejection_reason = reason
        self.save(update_fields=["status", "issued_by", "rejection_reason"])
