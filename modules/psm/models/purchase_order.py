from decimal import Decimal

from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel
from modules.psm.models.indent import Indent
from modules.psm.models.item import ItemMaster
from modules.psm.models.vendor import Vendor


class ProcurementMethod(models.TextChoices):
    DIRECT = "DIRECT", "Direct Procurement"
    QUOTATION = "QUOTATION", "Quotation / Committee"
    TENDER = "TENDER", "Open / Limited Tender"
    GEM = "GEM", "Government e-Marketplace (GeM)"


class POStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    ISSUED = "ISSUED", "Issued"
    PARTIALLY_DELIVERED = "PARTIALLY_DELIVERED", "Partially Delivered"
    COMPLETED = "COMPLETED", "Completed"
    CANCELLED = "CANCELLED", "Cancelled"


class PurchaseOrder(TimeStampedModel):
    po_number = models.CharField(max_length=64, unique=True)
    indent = models.OneToOneField(
        Indent,
        related_name="purchase_order",
        on_delete=models.PROTECT,
    )
    vendor = models.ForeignKey(
        Vendor,
        related_name="purchase_orders",
        on_delete=models.PROTECT,
    )
    procurement_method = models.CharField(
        max_length=32,
        choices=ProcurementMethod.choices,
        default=ProcurementMethod.DIRECT,
    )
    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    status = models.CharField(
        max_length=32,
        choices=POStatus.choices,
        default=POStatus.DRAFT,
        db_index=True,
    )
    delivery_due_date = models.DateField(null=True, blank=True)
    issued_by_user_id = models.IntegerField(null=True, blank=True)
    issued_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "psm_purchase_order"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=Q(total_amount__gte=0),
                name="psm_po_total_non_negative",
            ),
            models.CheckConstraint(
                condition=Q(status__in=POStatus.values),
                name="psm_po_status_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.po_number} -> {self.vendor.name} [{self.status}]"


class POLineItem(TimeStampedModel):
    purchase_order = models.ForeignKey(
        PurchaseOrder,
        related_name="lines",
        on_delete=models.CASCADE,
    )
    item_master = models.ForeignKey(
        ItemMaster,
        related_name="po_lines",
        on_delete=models.PROTECT,
    )
    quantity_ordered = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = "psm_po_line_item"
        constraints = [
            models.CheckConstraint(
                condition=Q(quantity_ordered__gt=0),
                name="psm_po_line_qty_positive",
            ),
            models.CheckConstraint(
                condition=Q(unit_price__gte=0),
                name="psm_po_line_unit_price_non_negative",
            ),
        ]

    @property
    def total_cost(self) -> Decimal:
        return Decimal(self.quantity_ordered) * self.unit_price
