"""Inventory catalog and immutable stock transactions (CFR-DEPT-004, BR-DEPT-016)."""

import uuid

from django.db import models

from modules.dept.models.department import Department


class InventoryItem(models.Model):
    CATEGORY_CHOICES = [
        ("EQUIPMENT", "Equipment"),
        ("CONSUMABLE", "Consumable"),
        ("FURNITURE", "Furniture"),
        ("OTHER", "Other"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name="inventory_items",
    )
    item_code = models.CharField(max_length=64)
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=64, choices=CATEGORY_CHOICES, default="CONSUMABLE")
    quantity = models.IntegerField(default=0)
    unit = models.CharField(max_length=32, default="units")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dept_inventory_item"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["department", "item_code"],
                name="unique_dept_inventory_item",
            ),
            models.CheckConstraint(
                condition=models.Q(quantity__gte=0),
                name="non_negative_inventory_quantity",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.item_code}): {self.quantity} {self.unit}"


class StockTransaction(models.Model):
    TRANSACTION_CHOICES = [
        ("INSERTION", "Insertion"),
        ("ISSUANCE", "Issuance"),
        ("ADJUSTMENT", "Adjustment"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    inventory_item = models.ForeignKey(
        InventoryItem,
        on_delete=models.PROTECT,
        related_name="transactions",
    )
    transaction_type = models.CharField(max_length=16, choices=TRANSACTION_CHOICES)
    quantity_delta = models.IntegerField()
    balance_after = models.IntegerField()
    performed_by_id = models.CharField(max_length=64)
    related_request_id = models.UUIDField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "dept_stock_transaction"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.transaction_type} {self.quantity_delta} on {self.inventory_item_id}"
