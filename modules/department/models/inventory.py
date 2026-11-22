from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower

from core.db.mixins import TimeStampedModel
from modules.department.domain import state_machine as sm


class InventoryItem(TimeStampedModel):
    """`current_quantity` is the running total of the StockMovement ledger (Step 2.7)."""

    department = models.ForeignKey(
        "department.Department", on_delete=models.PROTECT, related_name="inventory_items"
    )
    name = models.CharField(max_length=120)
    unit = models.CharField(max_length=20, default="unit")
    current_quantity = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "department_inventory_item"
        constraints = [
            models.CheckConstraint(
                condition=Q(current_quantity__gte=0), name="dept_item_not_negative"
            ),
            models.UniqueConstraint(Lower("name"), "department", name="dept_item_unique_name"),
        ]
        indexes = [models.Index(fields=["department", "-id"], name="dept_item_list_idx")]


class StockMovementQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise TypeError("Stock movements are immutable (BR-DEPT-016).")

    def delete(self):
        raise TypeError("Stock movements are immutable (BR-DEPT-016).")


class StockMovement(models.Model):
    """Append-only: no update or delete path exists (BR-DEPT-016, AFR-DEPT-014, AFR-DEPT-015)."""

    RECEIPT, ISSUE = "receipt", "issue"

    item = models.ForeignKey(InventoryItem, on_delete=models.PROTECT, related_name="movements")
    kind = models.CharField(max_length=8, choices=[(RECEIPT, "Receipt"), (ISSUE, "Issue")])
    quantity = models.PositiveIntegerField()
    actor_id = models.IntegerField()
    stock_request = models.OneToOneField(
        "department.StockRequest",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="movement",
    )
    note = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = StockMovementQuerySet.as_manager()

    class Meta:
        db_table = "department_stock_movement"
        constraints = [
            models.CheckConstraint(condition=Q(quantity__gt=0), name="dept_move_positive"),
            models.CheckConstraint(
                condition=Q(kind="issue", stock_request__isnull=False)
                | Q(kind="receipt", stock_request__isnull=True),
                name="dept_move_issue_has_request",
            ),
        ]
        indexes = [models.Index(fields=["item", "-id"], name="dept_move_item_idx")]

    def __str__(self) -> str:
        return f"{self.kind} {self.quantity} of item {self.item_id}"

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise TypeError("Stock movements are immutable (BR-DEPT-016).")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise TypeError("Stock movements are immutable (BR-DEPT-016).")


_STOCK_STATES = [sm.STOCK_PENDING, sm.STOCK_APPROVED, sm.STOCK_REJECTED, sm.STOCK_ISSUED]


class StockRequest(TimeStampedModel):
    STATUS = [
        (sm.STOCK_PENDING, "Pending HOD approval"),
        (sm.STOCK_APPROVED, "Approved for issuance"),
        (sm.STOCK_REJECTED, "Rejected"),
        (sm.STOCK_ISSUED, "Issued"),
    ]

    department = models.ForeignKey(
        "department.Department", on_delete=models.PROTECT, related_name="stock_requests"
    )
    item = models.ForeignKey(InventoryItem, on_delete=models.PROTECT, related_name="requests")
    requester_id = models.IntegerField()
    quantity = models.PositiveIntegerField()
    purpose = models.CharField(max_length=300, blank=True)
    status = models.CharField(max_length=12, choices=STATUS, default=sm.STOCK_PENDING)
    decided_by = models.IntegerField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    reason = models.CharField(max_length=500, blank=True)
    issued_by = models.IntegerField(null=True, blank=True)
    issued_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "department_stock_request"
        constraints = [
            models.CheckConstraint(condition=Q(quantity__gt=0), name="dept_req_positive"),
            models.CheckConstraint(
                condition=Q(status__in=_STOCK_STATES), name="dept_req_status_known"
            ),
            models.CheckConstraint(
                condition=~Q(status="issued") | Q(issued_by__isnull=False),
                name="dept_req_issued_has_issuer",
            ),
        ]
        indexes = [
            models.Index(fields=["department", "status", "-id"], name="dept_req_queue_idx"),
            models.Index(fields=["requester_id", "-id"], name="dept_req_mine_idx"),
        ]
