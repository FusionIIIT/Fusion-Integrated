from django.db import models
from django.db.models import F, Q

from core.db.mixins import TimeStampedModel
from modules.psm.models.item import ItemMaster


class StockTransactionType(models.TextChoices):
    RECEIPT_CREDIT = "RECEIPT_CREDIT", "Goods Receipt Credit"
    INTERNAL_ISSUE = "INTERNAL_ISSUE", "Internal Departmental Issue"
    RESERVATION_LOCK = "RESERVATION_LOCK", "Stock Reservation Lock"
    RESERVATION_RELEASE = "RESERVATION_RELEASE", "Stock Reservation Release"
    ADJUSTMENT = "ADJUSTMENT", "Inventory Audit Adjustment"


class StockItem(TimeStampedModel):
    item_master = models.OneToOneField(
        ItemMaster,
        related_name="stock",
        on_delete=models.CASCADE,
    )
    quantity_on_hand = models.PositiveIntegerField(default=0)
    quantity_reserved = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "psm_stock_item"
        constraints = [
            models.CheckConstraint(
                condition=Q(quantity_reserved__lte=F("quantity_on_hand")),
                name="psm_stock_reserved_lte_on_hand",
            )
        ]

    @property
    def available_quantity(self) -> int:
        return max(0, self.quantity_on_hand - self.quantity_reserved)

    def __str__(self) -> str:
        code = self.item_master.item_code
        return f"{code}: OnHand={self.quantity_on_hand}, Res={self.quantity_reserved}"


class StockLedger(TimeStampedModel):
    stock_item = models.ForeignKey(
        StockItem,
        related_name="ledger_entries",
        on_delete=models.CASCADE,
    )
    transaction_type = models.CharField(
        max_length=32,
        choices=StockTransactionType.choices,
    )
    quantity = models.IntegerField()
    balance_after = models.PositiveIntegerField()
    reference_id = models.CharField(max_length=128, blank=True)
    recorded_by_user_id = models.IntegerField()
    remarks = models.TextField(blank=True)

    class Meta:
        db_table = "psm_stock_ledger"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        code = self.stock_item.item_master.item_code
        return f"{code} | {self.transaction_type} | Qty={self.quantity}"
