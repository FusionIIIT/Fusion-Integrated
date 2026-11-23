from django.db import models

from core.db.mixins import TimeStampedModel
from modules.phc.domain.state_machine import RequisitionStatus
from modules.phc.models.inventory import InventoryItem


class Requisition(TimeStampedModel):
    originator_user_id = models.IntegerField()
    purpose = models.CharField(max_length=500)
    status = models.CharField(max_length=24, choices=RequisitionStatus.CHOICES,
                              default=RequisitionStatus.PENDING_APPROVAL)
    decided_by_user_id = models.IntegerField(null=True, blank=True)
    decision_note = models.CharField(max_length=500, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    fulfilled_by_user_id = models.IntegerField(null=True, blank=True)
    fulfilled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "phc_requisition"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status="pending_approval") | models.Q(
                    decided_at__isnull=False),
                name="phc_requisition_decided_has_time"),
            models.CheckConstraint(
                condition=~models.Q(status="fulfilled") | models.Q(fulfilled_at__isnull=False),
                name="phc_requisition_fulfilled_has_time"),
        ]

    def __str__(self) -> str:
        return f"Requisition {self.pk}"


class RequisitionLine(models.Model):
    requisition = models.ForeignKey(Requisition, on_delete=models.CASCADE,
                                    related_name="lines")
    item = models.ForeignKey(InventoryItem, on_delete=models.PROTECT,
                             related_name="requisition_lines")
    quantity = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = "phc_requisition_line"
        ordering = ("id",)
        constraints = [
            models.CheckConstraint(condition=models.Q(quantity__gt=0),
                                   name="phc_line_quantity_positive"),
            models.UniqueConstraint(fields=("requisition", "item"),
                                    name="phc_line_item_once"),
        ]

    def __str__(self) -> str:
        return f"{self.item_id} x {self.quantity}"
