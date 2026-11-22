from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel
from modules.psm.models.purchase_order import POLineItem, PurchaseOrder


class GRNStatus(models.TextChoices):
    INSPECTION_PENDING = "INSPECTION_PENDING", "Inspection Pending"
    ACCEPTED = "ACCEPTED", "Accepted"
    DISCREPANT = "DISCREPANT", "Discrepant"
    CLOSED = "CLOSED", "Closed"


class GoodsReceiptNote(TimeStampedModel):
    grn_number = models.CharField(max_length=64, unique=True)
    purchase_order = models.ForeignKey(
        PurchaseOrder,
        related_name="goods_receipts",
        on_delete=models.PROTECT,
    )
    store_keeper_user_id = models.IntegerField()
    challan_number = models.CharField(max_length=128, blank=True)
    invoice_number = models.CharField(max_length=128, blank=True)
    receipt_date = models.DateField()
    status = models.CharField(
        max_length=32,
        choices=GRNStatus.choices,
        default=GRNStatus.INSPECTION_PENDING,
        db_index=True,
    )
    indentor_acknowledged = models.BooleanField(default=False)
    indentor_acknowledged_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "psm_goods_receipt_note"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(status__in=GRNStatus.values),
                name="psm_grn_status_valid",
            )
        ]

    def __str__(self) -> str:
        return f"{self.grn_number} for {self.purchase_order.po_number} [{self.status}]"


class GRNItem(TimeStampedModel):
    grn = models.ForeignKey(
        GoodsReceiptNote,
        related_name="items",
        on_delete=models.CASCADE,
    )
    po_line_item = models.ForeignKey(
        POLineItem,
        related_name="grn_items",
        on_delete=models.PROTECT,
    )
    quantity_received = models.PositiveIntegerField()
    quantity_accepted = models.PositiveIntegerField(default=0)
    quantity_rejected = models.PositiveIntegerField(default=0)
    rejection_remarks = models.TextField(blank=True)

    class Meta:
        db_table = "psm_grn_item"
        constraints = [
            models.CheckConstraint(
                condition=Q(quantity_received__gte=0),
                name="psm_grn_item_received_non_negative",
            ),
            models.CheckConstraint(
                condition=Q(quantity_accepted__gte=0),
                name="psm_grn_item_accepted_non_negative",
            ),
            models.CheckConstraint(
                condition=Q(quantity_rejected__gte=0),
                name="psm_grn_item_rejected_non_negative",
            ),
        ]
