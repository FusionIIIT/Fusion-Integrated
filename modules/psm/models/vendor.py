# Vendor master data and append-only version history (BR-PSM-012, BR-PSM-025, PSM-UC-019).
from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel


class Vendor(TimeStampedModel):
    code = models.CharField(max_length=32, unique=True)
    name = models.CharField(max_length=200)
    gstin = models.CharField(max_length=15, blank=True)
    bank_account_number = models.CharField(max_length=34, blank=True)
    bank_ifsc = models.CharField(max_length=11, blank=True)
    bank_name = models.CharField(max_length=120, blank=True)
    compliance_documents = models.JSONField(default=list, blank=True)
    contact_email = models.EmailField(blank=True)
    is_verified = models.BooleanField(default=False)
    verified_by_user_id = models.IntegerField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    version = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "psm_vendor"
        ordering = ["name"]
        constraints = [
            models.CheckConstraint(
                condition=~Q(is_verified=True) | Q(verified_at__isnull=False),
                name="psm_vendor_verified_has_timestamp",
            ),
        ]
        indexes = [
            models.Index(fields=["is_verified", "name"], name="psm_vendor_verified_name_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.code} {self.name}"


class VendorVersion(models.Model):
    """Append-only snapshot captured on vendor onboarding and every update (BR-PSM-025)."""

    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="versions")
    version = models.PositiveIntegerField()
    snapshot = models.JSONField(default=dict)
    changed_by_user_id = models.IntegerField()
    change_reason = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "psm_vendor_version"
        ordering = ["-version"]
        constraints = [
            models.UniqueConstraint(fields=["vendor", "version"], name="psm_vendor_version_unique"),
        ]
        indexes = [
            models.Index(fields=["vendor", "-version"], name="psm_vendor_ver_idx"),
        ]

    def __str__(self) -> str:
        return f"vendor#{self.vendor_id} v{self.version}"
