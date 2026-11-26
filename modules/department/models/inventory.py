from django.db import models

from core.db.mixins import TimeStampedModel


class InventoryItem(TimeStampedModel):
    """Represents an inventory item within a department."""
    department = models.ForeignKey("department.Department", on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    unit = models.CharField(max_length=20)
    quantity = models.IntegerField(default=0)

    class Meta:
        unique_together = (('department', 'name'),)
        constraints = [
            models.CheckConstraint(
                check=models.Q(quantity__gte=0),
                name="dept_item_qty_nonneg"
            )
        ]
        db_table = "department_inventory_item"

    def __str__(self):
        return f"{self.name} ({self.unit}) in {self.department.name}"


class StockRequest(TimeStampedModel):
    """Represents a request for stock from a department."""
    STATE_CHOICES = (
        ('pending_hod_approval', 'Pending HOD Approval'),
        ('approved_for_issuance', 'Approved for Issuance'),
        ('rejected', 'Rejected'),
        ('issued', 'Issued'),
    )

    department = models.ForeignKey("department.Department", on_delete=models.CASCADE)
    item = models.ForeignKey("department.InventoryItem", on_delete=models.CASCADE)
    requester_user_id = models.IntegerField(null=True, blank=True)
    quantity = models.IntegerField()
    state = models.CharField(
        max_length=30,
        choices=STATE_CHOICES,
        default='pending_hod_approval'
    )
    decided_by_user_id = models.IntegerField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    issued_by_user_id = models.IntegerField(null=True, blank=True)
    issued_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(quantity__gt=0),
                name="dept_req_qty_positive"
            )
        ]
        db_table = "department_stock_request"

    def __str__(self):
        return f"Request for {self.item.name} ({self.quantity}) in {self.department.name} - {self.state}"


class StockMovement(TimeStampedModel):
    """Represents a movement of stock (insertion or issuance)."""
    KIND_CHOICES = (
        ('insertion', 'Insertion'),
        ('issuance', 'Issuance'),
    )

    item = models.ForeignKey("department.InventoryItem", on_delete=models.CASCADE)
    kind = models.CharField(max_length=10, choices=KIND_CHOICES)
    quantity = models.IntegerField()
    request = models.ForeignKey("department.StockRequest", on_delete=models.SET_NULL, null=True, blank=True)
    actor_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "department_stock_movement"

    def __str__(self):
        return f"{self.kind} of {self.quantity} {self.item.name} by {self.actor_user_id}"

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("StockMovement must be append-only and cannot be updated.")
        super().save(*args, **kwargs)

    def delete(self):
        raise ValueError("StockMovement records are append-only and cannot be deleted.")
