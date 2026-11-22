from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel


class VendorStatus(models.TextChoices):
    PENDING_VERIFICATION = "PENDING_VERIFICATION", "Pending Verification"
    VERIFIED = "VERIFIED", "Verified"
    BLACKLISTED = "BLACKLISTED", "Blacklisted"
    SUSPENDED = "SUSPENDED", "Suspended"


class Vendor(TimeStampedModel):
    vendor_code = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=255)
    gstin = models.CharField(max_length=15, unique=True)
    email = models.EmailField()
    phone = models.CharField(max_length=32)
    address = models.TextField(blank=True)
    bank_account_number = models.CharField(max_length=64, blank=True)
    bank_ifsc = models.CharField(max_length=32, blank=True)
    status = models.CharField(
        max_length=32,
        choices=VendorStatus.choices,
        default=VendorStatus.PENDING_VERIFICATION,
        db_index=True,
    )
    verified_by_user_id = models.IntegerField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "psm_vendor"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(status__in=VendorStatus.values),
                name="psm_vendor_status_valid",
            )
        ]

    def __str__(self) -> str:
        return f"{self.vendor_code} - {self.name} ({self.status})"
