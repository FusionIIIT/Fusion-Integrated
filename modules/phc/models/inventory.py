from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel


class InventoryItem(TimeStampedModel):
    name = models.CharField(max_length=160, unique=True)
    unit = models.CharField(max_length=40, default="units")
    reorder_threshold = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "phc_inventory_item"
        ordering = ["name", "id"]
        constraints = [models.CheckConstraint(
            condition=Q(reorder_threshold__gt=0),
            name="phc_inventory_threshold_positive")]
        indexes = [models.Index(fields=["is_active", "name"],
                                name="phc_inventory_active_name_idx")]


class InventoryMovement(TimeStampedModel):
    item = models.ForeignKey(InventoryItem, on_delete=models.PROTECT,
                             related_name="movements")
    quantity_delta = models.IntegerField()
    reason = models.CharField(max_length=200, blank=True)
    actor_user_id = models.PositiveBigIntegerField()

    class Meta:
        db_table = "phc_inventory_movement"
        ordering = ["-created_at", "-id"]
        constraints = [models.CheckConstraint(
            condition=~Q(quantity_delta=0), name="phc_movement_nonzero")]
        indexes = [models.Index(fields=["item", "-created_at", "-id"],
                                name="phc_movement_item_created_idx")]


class LowStockAlert(TimeStampedModel):
    item = models.ForeignKey(InventoryItem, on_delete=models.PROTECT,
                             related_name="low_stock_alerts")
    movement = models.OneToOneField(InventoryMovement, on_delete=models.PROTECT,
                                    related_name="low_stock_alert")
    quantity_after = models.PositiveIntegerField()
    reorder_threshold = models.PositiveIntegerField()

    class Meta:
        db_table = "phc_low_stock_alert"
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["-created_at"], name="phc_low_alert_created_idx")]
