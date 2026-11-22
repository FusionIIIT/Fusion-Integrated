from django.core.exceptions import ValidationError
from django.db import models

from core.db.mixins import TimeStampedModel


class InventoryItem(TimeStampedModel):
    """A department inventory item and its current stock level."""

    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    unit = models.CharField(max_length=40)
    quantity = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        db_table = "department_inventory_item"
        ordering = ["name"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gte=0),
                name="dept_inventory_qty_nonnegative",
            ),
        ]

    def clean(self):
        super().clean()
        self.name = (self.name or "").strip()
        self.unit = (self.unit or "").strip()

        if not self.name:
            raise ValidationError({"name": "An item name is required."})

        if not self.unit:
            raise ValidationError({"unit": "A unit of measurement is required."})

    def __str__(self):
        return f"{self.name} ({self.quantity} {self.unit})"


class StockRequest(TimeStampedModel):
    """A Faculty request for inventory stock requiring an HOD decision."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending HOD Approval"
        APPROVED = "approved", "Approved for Issuance"
        REJECTED = "rejected", "Rejected"
        ISSUED = "issued", "Issued"

    item = models.ForeignKey(
        InventoryItem,
        on_delete=models.PROTECT,
        related_name="stock_requests",
    )
    requested_by_user_id = models.IntegerField(db_index=True)
    requested_quantity = models.PositiveIntegerField()
    purpose = models.TextField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )

    submitted_at = models.DateTimeField()
    decided_at = models.DateTimeField(null=True, blank=True)
    decided_by_user_id = models.IntegerField(null=True, blank=True)
    decision_role = models.CharField(max_length=60, blank=True)
    decision_note = models.TextField(blank=True)

    issued_at = models.DateTimeField(null=True, blank=True)
    issued_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "department_stock_request"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(requested_quantity__gt=0),
                name="dept_stock_req_qty_positive",
            ),
        ]
        indexes = [
            models.Index(
                fields=["status", "created_at"],
                name="dept_stock_status_created_idx",
            ),
        ]

    def clean(self):
        super().clean()

        if self.requested_quantity <= 0:
            raise ValidationError({
                "requested_quantity": "Requested quantity must be greater than zero."
            })

        if not (self.purpose or "").strip():
            raise ValidationError({
                "purpose": "A purpose is required for a stock request."
            })

    def __str__(self):
        return (
            f"Request #{self.pk}: {self.item.name} "
            f"x {self.requested_quantity} ({self.status})"
        )


class StockMovement(TimeStampedModel):
    """Append-only audit record for inventory stock changes."""

    class MovementType(models.TextChoices):
        INSERTION = "insertion", "Stock Insertion"
        ISSUANCE = "issuance", "Stock Issuance"

    item = models.ForeignKey(
        InventoryItem,
        on_delete=models.PROTECT,
        related_name="movements",
    )
    movement_type = models.CharField(
        max_length=20,
        choices=MovementType.choices,
    )
    quantity = models.PositiveIntegerField()
    quantity_before = models.PositiveIntegerField()
    quantity_after = models.PositiveIntegerField()
    performed_by_user_id = models.IntegerField(db_index=True)
    performed_by_role = models.CharField(max_length=60)
    stock_request = models.ForeignKey(
        StockRequest,
        on_delete=models.PROTECT,
        related_name="movements",
        null=True,
        blank=True,
    )
    note = models.TextField(blank=True)

    class Meta:
        db_table = "department_stock_movement"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity__gt=0),
                name="dept_stock_move_qty_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(quantity_after__gte=0),
                name="dept_stock_move_after_nonnegative",
            ),
        ]
        indexes = [
            models.Index(
                fields=["item", "created_at"],
                name="dept_move_item_created_idx",
            ),
        ]

    def clean(self):
        super().clean()

        if self.quantity <= 0:
            raise ValidationError({
                "quantity": "Movement quantity must be greater than zero."
            })

        if self.movement_type == self.MovementType.INSERTION:
            if self.quantity_after != self.quantity_before + self.quantity:
                raise ValidationError(
                    "An insertion must increase stock by the movement quantity."
                )

        elif self.movement_type == self.MovementType.ISSUANCE:
            if self.quantity_before - self.quantity != self.quantity_after:
                raise ValidationError(
                    "An issuance must decrease stock by the movement quantity."
                )

        else:
            raise ValidationError({
                "movement_type": "Unsupported stock movement type."
            })

    def save(self, *args, **kwargs):
        # Audit records are immutable after creation.
        if self.pk is not None:
            raise ValidationError("Stock movement records cannot be modified.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Stock movement records cannot be deleted.")

    def __str__(self):
        return (
            f"{self.movement_type}: {self.item.name} "
            f"x {self.quantity}"
        )
