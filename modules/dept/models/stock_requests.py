"""Stock request model and lifecycle (CFR-DEPT-005, BW-DEPT-01, BW-DEPT-02)."""

import uuid

from django.db import models

from modules.dept.models.department import Department
from modules.dept.models.inventory import InventoryItem


class StockRequest(models.Model):
    STATUS_CHOICES = [
        ("SUBMITTED", "Submitted"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("ISSUED", "Issued"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name="stock_requests",
    )
    inventory_item = models.ForeignKey(
        InventoryItem,
        on_delete=models.PROTECT,
        related_name="requests",
    )
    requested_by_id = models.CharField(max_length=64)
    requested_quantity = models.IntegerField()
    purpose = models.TextField()
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="SUBMITTED")
    hod_decision_by_id = models.CharField(max_length=64, blank=True, default="")
    hod_decision_at = models.DateTimeField(null=True, blank=True)
    hod_remarks = models.TextField(blank=True, default="")
    issued_by_id = models.CharField(max_length=64, blank=True, default="")
    issued_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dept_stock_request"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(requested_quantity__gt=0),
                name="positive_stock_request_quantity",
            ),
        ]
        indexes = [
            models.Index(fields=["department", "status", "-created_at"]),
            models.Index(fields=["requested_by_id", "status"]),
        ]

    def __str__(self) -> str:
        return f"StockRequest {self.requested_quantity} x {self.inventory_item_id} [{self.status}]"
