"""Inventory Stock and Procurement Requisition models (CFR-PHC-006, CFR-PHC-007)."""
from django.db import models

from core.db.mixins import TimeStampedModel
from modules.phc.domain.entities import RequisitionStatus


class InventoryItem(TimeStampedModel):
    """PHC medicine or supply item with reorder threshold (AFR-PHC-024, 025)."""
    item_code = models.CharField(max_length=50, unique=True, db_index=True)
    name = models.CharField(max_length=150)
    category = models.CharField(max_length=80, default="Medicine")
    stock_level = models.IntegerField(default=0)
    reorder_threshold = models.IntegerField(default=10)
    unit = models.CharField(max_length=30, default="units")
    description = models.TextField(blank=True)

    class Meta:
        db_table = "phc_inventory_items"
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.item_code}) - Stock: {self.stock_level} {self.unit}"


class InventoryStockAdjustment(models.Model):
    """Log of manual stock addition/deductions (AFR-PHC-024, 037; BR-PHC-09)."""
    TYPE_CHOICES = [
        ("ADD", "Add Stock"),
        ("DEDUCT", "Deduct Stock"),
    ]

    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name="adjustments")
    adjustment_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    quantity = models.PositiveIntegerField()
    previous_stock = models.IntegerField()
    new_stock = models.IntegerField()
    reason = models.CharField(max_length=255)
    adjusted_by_user_id = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "phc_inventory_adjustments"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.adjustment_type} {self.quantity} for {self.item.name} by User {self.adjusted_by_user_id}"


class ProcurementRequisition(TimeStampedModel):
    """Cross-actor inventory requisition lifecycle (CW-PHC-02, BW-PHC-03, BW-PHC-04)."""
    STATUS_CHOICES = [
        (s.value, s.value) for s in RequisitionStatus
    ]

    requisition_number = models.CharField(max_length=64, unique=True, db_index=True)
    originator_user_id = models.IntegerField(db_index=True)
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default=RequisitionStatus.PENDING_APPROVAL.value,
        db_index=True,
    )
    justification = models.TextField()
    approver_user_id = models.IntegerField(null=True, blank=True)
    decision_at = models.DateTimeField(null=True, blank=True)
    decision_remarks = models.TextField(blank=True)
    fulfilled_at = models.DateTimeField(null=True, blank=True)
    fulfilled_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "phc_procurement_requisitions"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Requisition {self.requisition_number} ({self.status})"


class RequisitionItem(models.Model):
    """Item line in a procurement requisition (AFR-PHC-027)."""
    requisition = models.ForeignKey(ProcurementRequisition, on_delete=models.CASCADE, related_name="items")
    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name="requisition_entries")
    quantity_requested = models.PositiveIntegerField()

    class Meta:
        db_table = "phc_requisition_items"

    def __str__(self) -> str:
        return f"{self.quantity_requested} x {self.item.name} for {self.requisition.requisition_number}"
