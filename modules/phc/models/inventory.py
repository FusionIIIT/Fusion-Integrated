from django.db import models

from core.db.mixins import TimeStampedModel
from modules.phc.models._immutable import AppendOnlyModel


class InventoryItem(TimeStampedModel):
    name = models.CharField(max_length=160, unique=True)
    unit = models.CharField(max_length=40)
    stock_level = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    reorder_threshold = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        db_table = "phc_inventory_item"
        ordering = ("name",)
        constraints = [
            models.CheckConstraint(condition=models.Q(stock_level__gte=0),
                                   name="phc_stock_nonnegative"),
            models.CheckConstraint(condition=models.Q(reorder_threshold__gte=0),
                                   name="phc_threshold_nonnegative"),
        ]

    def __str__(self) -> str:
        return self.name


class StockAdjustment(AppendOnlyModel):
    item = models.ForeignKey(InventoryItem, on_delete=models.PROTECT,
                             related_name="adjustments")
    delta = models.DecimalField(max_digits=12, decimal_places=2)
    level_after = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.CharField(max_length=300, blank=True)
    adjusted_by_user_id = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "phc_stock_adjustment"
        indexes = [
            models.Index(fields=["created_at"], name="phc_adjustment_time_idx"),
        ]
        constraints = [
            models.CheckConstraint(condition=~models.Q(delta=0),
                                   name="phc_adjustment_nonzero"),
        ]

    def __str__(self) -> str:
        return f"{self.item_id} {self.delta}"


class LowStockAlert(AppendOnlyModel):
    item = models.ForeignKey(InventoryItem, on_delete=models.PROTECT,
                             related_name="alerts")
    adjustment = models.OneToOneField(StockAdjustment, on_delete=models.PROTECT,
                                      related_name="alert")
    level = models.DecimalField(max_digits=12, decimal_places=2)
    threshold = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "phc_low_stock_alert"
        indexes = [
            models.Index(fields=["-created_at"], name="phc_alert_recent_idx"),
        ]
        constraints = [
            models.CheckConstraint(condition=models.Q(level__lt=models.F("threshold")),
                                   name="phc_alert_only_below_threshold"),
        ]

    def __str__(self) -> str:
        return f"Low stock: {self.item_id}"
