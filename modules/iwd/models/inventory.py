from django.db import models
from django.db.models import Q

from modules.iwd.models.complaint import Complaint
from modules.iwd.models.estimate import RepairEstimate


class InventoryItem(models.Model):
    """Inventory item tracked by IWD."""

    item_code = models.CharField(max_length=50, unique=True, db_index=True)
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=50)
    unit = models.CharField(max_length=30)
    current_stock = models.IntegerField(default=0)

    class Meta:
        db_table = "iwd_inventory_item"
        constraints = [
            models.CheckConstraint(
                check=Q(current_stock__gte=0),
                name="iwd_non_negative_inventory_stock",
            ),
        ]


class MaterialIssueLedger(models.Model):
    """Append-only ledger of material issues."""

    complaint = models.ForeignKey(
        Complaint, on_delete=models.CASCADE, related_name="material_issues"
    )
    item = models.ForeignKey(InventoryItem, on_delete=models.PROTECT)
    quantity = models.IntegerField()
    issued_by_user_id = models.IntegerField()
    issued_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "iwd_material_issue_ledger"


class ProcurementOrder(models.Model):
    """Procurement or bidding action."""

    TYPE_CHOICES = [
        ("internal_quotation", "Internal Quotation"),
        ("external_bidding", "External Bidding"),
    ]

    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE)
    estimate = models.ForeignKey(RepairEstimate, on_delete=models.CASCADE)
    procurement_type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    vendor_name = models.CharField(max_length=255)
    vendor_details = models.TextField(blank=True, default="")
    quoted_amount = models.DecimalField(max_digits=12, decimal_places=2)
    compliance_confirmed = models.BooleanField(default=False)
    status = models.CharField(max_length=30, default="completed")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "iwd_procurement_order"
