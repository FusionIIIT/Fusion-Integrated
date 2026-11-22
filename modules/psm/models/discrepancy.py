from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel
from modules.psm.models.goods_receipt import GoodsReceiptNote


class DiscrepancyType(models.TextChoices):
    SHORTAGE = "SHORTAGE", "Shortage"
    DAMAGED = "DAMAGED", "Damaged Items"
    SPEC_MISMATCH = "SPEC_MISMATCH", "Specification Mismatch"
    WRONG_ITEM = "WRONG_ITEM", "Wrong Item Delivered"


class DiscrepancyStatus(models.TextChoices):
    OPEN_HOLD_PAYMENT = "OPEN_HOLD_PAYMENT", "Open - Payment on Hold"
    VENDOR_NOTIFIED = "VENDOR_NOTIFIED", "Vendor Notified"
    REPLACED = "REPLACED", "Replaced"
    CREDIT_NOTE_ISSUED = "CREDIT_NOTE_ISSUED", "Credit Note Issued"
    RESOLVED = "RESOLVED", "Resolved"


class DiscrepancyReport(TimeStampedModel):
    discrepancy_code = models.CharField(max_length=64, unique=True)
    grn = models.OneToOneField(
        GoodsReceiptNote,
        related_name="discrepancy_report",
        on_delete=models.CASCADE,
    )
    reported_by_user_id = models.IntegerField()
    discrepancy_type = models.CharField(
        max_length=32,
        choices=DiscrepancyType.choices,
        default=DiscrepancyType.DAMAGED,
    )
    details = models.TextField()
    status = models.CharField(
        max_length=32,
        choices=DiscrepancyStatus.choices,
        default=DiscrepancyStatus.OPEN_HOLD_PAYMENT,
        db_index=True,
    )
    resolution_summary = models.TextField(blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "psm_discrepancy_report"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(status__in=DiscrepancyStatus.values),
                name="psm_discrepancy_status_valid",
            )
        ]

    def __str__(self) -> str:
        return f"{self.discrepancy_code} ({self.discrepancy_type}) [{self.status}]"
