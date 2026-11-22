# Inventory and replenishment models for VHMS.
from django.db import models
from django.db.models import CheckConstraint, Index, Q

from core.db.mixins import TimeStampedModel


class InventoryItem(TimeStampedModel):
    # VH inventory items including linen, utensils, consumables.
    item_name = models.CharField(max_length=100, unique=True, db_index=True)
    category = models.CharField(
        max_length=30,
        choices=[
            ("linen", "Linen"),
            ("utensils", "Utensils"),
            ("consumables", "Consumables"),
            ("other", "Other"),
        ],
        default="consumables",
    )
    current_quantity = models.PositiveIntegerField(default=0)
    minimum_threshold = models.PositiveIntegerField(default=10)
    unit = models.CharField(max_length=20, default="pieces")
    is_threshold_alert = models.BooleanField(default=False)

    class Meta:
        db_table = "vh_inventory_item"
        indexes = [
            Index(fields=["category", "is_threshold_alert"], name="vh_inv_cat_alert_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.item_name} (Qty: {self.current_quantity}, Min: {self.minimum_threshold})"


class InventoryReplenishment(TimeStampedModel):
    # Replenishment request reviewed and approved by VH In-Charge.
    item = models.ForeignKey(
        "vh.InventoryItem",
        on_delete=models.CASCADE,
        related_name="replenishments",
    )
    requested_quantity = models.PositiveIntegerField()
    status = models.CharField(
        max_length=20,
        default="pending",
        choices=[("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected")],
    )
    requested_by = models.IntegerField()  # Caretaker user_id
    approved_by = models.IntegerField(null=True, blank=True)  # VH In-Charge user_id
    approved_at = models.DateTimeField(null=True, blank=True)
    remarks = models.TextField(blank=True, default="")

    class Meta:
        db_table = "vh_inventory_replenishment"
        constraints = [
            CheckConstraint(
                condition=Q(requested_quantity__gt=0),
                name="vh_replenish_qty_gt_zero",
            ),
        ]

    def __str__(self) -> str:
        return f"Replenishment for {self.item.item_name}: {self.requested_quantity} ({self.status})"
