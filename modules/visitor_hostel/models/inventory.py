"""VH inventory. Quantity changes are a ledger, so usage can be reported."""
from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel
from modules.visitor_hostel.domain import inventory


class InventoryItem(TimeStampedModel):
    KIND = [(k, k.title()) for k in inventory.KINDS]

    name = models.CharField(max_length=120, unique=True)
    kind = models.CharField(max_length=12, choices=KIND)
    unit = models.CharField(max_length=20, default="pcs")
    quantity = models.PositiveIntegerField(default=0)
    min_threshold = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "vh_inventory_item"
        ordering = ["name"]
        constraints = [
            models.CheckConstraint(condition=Q(kind__in=inventory.KINDS),
                                   name="vh_inventory_kind_valid"),
        ]

    def __str__(self) -> str:
        return self.name


class InventoryAdjustment(models.Model):
    """Append-only. `quantity_after` makes each row checkable on its own."""

    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE,
                             related_name="adjustments")
    delta = models.IntegerField()
    quantity_after = models.PositiveIntegerField()
    reason = models.CharField(max_length=200)
    actor_user_id = models.IntegerField(null=True, blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "vh_inventory_adjustment"
        indexes = [models.Index(fields=["item", "at"], name="vh_adjustment_idx")]

    def __str__(self) -> str:
        return f"{self.item_id} {self.delta:+d}"


class InventoryAlert(models.Model):
    """BR-VH-041. At most one open alert per item, so a sagging stock level
    does not mail the Caretaker on every adjustment."""

    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE,
                             related_name="alerts")
    quantity_at_alert = models.PositiveIntegerField()
    threshold_at_alert = models.PositiveIntegerField()
    raised_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "vh_inventory_alert"
        constraints = [
            models.UniqueConstraint(fields=["item"], condition=Q(resolved_at__isnull=True),
                                    name="vh_one_open_alert_per_item"),
        ]

    def __str__(self) -> str:
        return f"alert {self.item_id} @{self.quantity_at_alert}"


class ReplenishmentRequirement(TimeStampedModel):
    STATUS = [("pending", "Pending"), ("approved", "Approved")]

    item = models.ForeignKey(InventoryItem, on_delete=models.PROTECT,
                             related_name="replenishments")
    quantity_required = models.PositiveIntegerField()
    note = models.CharField(max_length=300, blank=True)
    raised_by_user_id = models.IntegerField()
    status = models.CharField(max_length=10, choices=STATUS, default="pending")
    approved_by_user_id = models.IntegerField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "vh_replenishment_requirement"
        constraints = [
            models.CheckConstraint(condition=Q(quantity_required__gte=1),
                                   name="vh_replenishment_quantity_positive"),
            models.CheckConstraint(
                condition=~Q(status="approved") | Q(approved_at__isnull=False),
                name="vh_replenishment_approved_has_time"),
        ]
        indexes = [models.Index(fields=["status", "-created_at"],
                                name="vh_replenishment_idx")]

    def __str__(self) -> str:
        return f"replenish {self.item_id} x{self.quantity_required} {self.status}"
