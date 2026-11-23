from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel


class InventoryRequisition(TimeStampedModel):
    class State(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING = "pending_approval", "Pending Approval"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        FULFILLED = "fulfilled", "Fulfilled"

    originator_user_id = models.PositiveBigIntegerField()
    state = models.CharField(max_length=20, choices=State.choices,
                             default=State.DRAFT)
    decided_by_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    fulfilled_by_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    submitted_at = models.DateTimeField()

    class Meta:
        db_table = "phc_inventory_requisition"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["originator_user_id", "-created_at"],
                         name="phc_requisition_owner_idx"),
            models.Index(fields=["state", "created_at"],
                         name="phc_requisition_state_idx"),
        ]


class RequisitionLine(TimeStampedModel):
    requisition = models.ForeignKey(InventoryRequisition, on_delete=models.PROTECT,
                                    related_name="lines")
    item = models.ForeignKey("phc.InventoryItem", on_delete=models.PROTECT,
                             related_name="requisition_lines")
    quantity = models.PositiveIntegerField()

    class Meta:
        db_table = "phc_requisition_line"
        constraints = [
            models.CheckConstraint(condition=Q(quantity__gt=0),
                                   name="phc_requisition_quantity_positive"),
            models.UniqueConstraint(fields=["requisition", "item"],
                                    name="phc_requisition_item_unique"),
        ]
        indexes = [models.Index(fields=["requisition", "id"],
                                name="phc_requisition_line_list_idx")]
