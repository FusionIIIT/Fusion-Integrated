# Bill, LineItem, and Offline Settlement models for VHMS.
from django.db import models
from django.db.models import CheckConstraint, Index, Q

from core.db.mixins import TimeStampedModel


class Bill(TimeStampedModel):
    # Authoritative billing record for a booking or cancellation.
    booking = models.OneToOneField(
        "vh.Booking",
        on_delete=models.PROTECT,
        related_name="bill",
    )
    bill_number = models.CharField(max_length=32, unique=True, db_index=True)
    visitor_category = models.CharField(max_length=1)
    room_rent_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    meal_charge_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    cancellation_charge_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    billing_responsibility = models.CharField(max_length=20)
    status = models.CharField(
        max_length=20,
        default="generated",
        choices=[("generated", "Generated"), ("verified", "Verified"), ("settled", "Settled")],
        db_index=True,
    )
    is_immutable = models.BooleanField(default=False)
    verified_by = models.IntegerField(null=True, blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    finalized_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "vh_bill"
        indexes = [
            Index(fields=["status", "created_at"], name="vh_bill_status_created_idx"),
        ]

    def __str__(self) -> str:
        return f"Bill {self.bill_number} (Rs.{self.total_amount})"


class BillLineItem(TimeStampedModel):
    # Itemized charge on a VHMS bill.
    bill = models.ForeignKey(
        "vh.Bill",
        on_delete=models.CASCADE,
        related_name="items",
    )
    item_type = models.CharField(
        max_length=20,
        choices=[("room", "Room Rent"), ("meal", "Meal"), ("cancellation", "Cancellation Charge")],
    )
    description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=8, decimal_places=2, default=1.00)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = "vh_bill_line_item"

    def __str__(self) -> str:
        return f"{self.item_type}: {self.description} ({self.total_price})"


class BillSettlement(TimeStampedModel):
    # Records offline cash settlement of a bill.
    bill = models.OneToOneField(
        "vh.Bill",
        on_delete=models.PROTECT,
        related_name="settlement",
    )
    payment_mode = models.CharField(max_length=20, default="offline_cash")
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    settled_by = models.IntegerField()  # Caretaker user_id
    settled_at = models.DateTimeField(auto_now_add=True)
    receipt_number = models.CharField(max_length=50, blank=True, default="")
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "vh_bill_settlement"
        constraints = [
            CheckConstraint(
                condition=Q(amount_paid__gt=0),
                name="vh_settlement_amount_gt_zero",
            ),
        ]

    def __str__(self) -> str:
        return f"Settlement {self.receipt_number} for Bill {self.bill.bill_number}"
